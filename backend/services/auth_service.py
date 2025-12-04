import json
import logging
import re
import uuid
from datetime import datetime
from typing import Union

from bson import ObjectId

from common.exceptions import CustomAgentException, ErrorCode
from config import SETTINGS
from entities.bo import LoginRequest, WalletLoginRequest
from entities.dto import LoginResponse, NonceResponse, WalletLoginResponse, TokenResponse
from entities.enums import ChainType
from infra.db import users_col
from infra.redis_cache import REDIS
from utils.jwt_utils import generate_token_pair, verify_refresh_token
from utils.web3_utils import generate_nonce, get_message_to_sign, verify_signature

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
NONCE_EXPIRY_MINUTES = 1  # Nonce expires after 5 minutes
NONCE_KEY_PREFIX = "wallet_nonce:"  # Redis key prefix for nonce storage


def get_nonce_key(wallet_address: str) -> str:
    """Generate Redis key for storing nonce"""
    return f"{SETTINGS.REDIS_PREFIX}.{NONCE_KEY_PREFIX}{wallet_address}"


async def login(request: LoginRequest) -> LoginResponse:
    """
    Handle user login with username or email
    """
    try:
        # Find user by username or email
        user = await users_col.find_one({
            "$or": [
                {"username": request.username},
                {"email": request.username}
            ]
        })

        if not user:
            raise CustomAgentException(
                ErrorCode.INVALID_CREDENTIALS,
                "Invalid username/email or password"
            )

        if not user.get("password") == request.password:
            raise CustomAgentException(
                ErrorCode.INVALID_CREDENTIALS,
                "Invalid username/email or password"
            )

        # Generate token pair
        access_token, refresh_token = generate_token_pair(
            user_id=str(user["_id"]),
            username=user["username"],
            tenant_id=user.get("tenant_id"),
            wallet_address=user.get("wallet_address")
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                'id': str(user["_id"]),
                'username': user["username"],
                'wallet_address': user.get("wallet_address"),
                'chain_type': user.get("chain_type"),
                'email': user.get("email")
            },
            "access_token_expires_in": SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # convert to seconds
            "refresh_token_expires_in": SETTINGS.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # convert to seconds
        }
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.INTERNAL_ERROR,
            f"Login failed: {str(e)}"
        )


async def get_wallet_nonce(wallet_address: str) -> NonceResponse:
    """
    Get or generate nonce for wallet signature with expiry time using Redis
    """
    # Generate new nonce and message
    nonce = generate_nonce()
    message = get_message_to_sign(wallet_address, nonce)

    # Store nonce in Redis with expiry
    nonce_data = {
        "nonce": nonce,
        "created_at": datetime.utcnow().isoformat()
    }
    REDIS.set_value(
        get_nonce_key(wallet_address),
        json.dumps(nonce_data),
        ex=NONCE_EXPIRY_MINUTES * 60
    )

    # Check if user exists
    user = await users_col.find_one({"wallet_address": wallet_address})

    if not user:
        # Create temporary user entry with generated username
        temp_username = f"wallet_{wallet_address[-8:]}"

        # Check if the generated username exists
        existing_user = await users_col.find_one({"username": temp_username})
        if existing_user:
            temp_username = f"wallet_{wallet_address[-8:]}_{uuid.uuid4().hex[:4]}"

        # Create new user with tenant_id
        tenant_id = str(uuid.uuid4())
        user_data = {
            "username": temp_username,
            "wallet_address": wallet_address,
            "tenant_id": tenant_id,
            "create_time": datetime.utcnow(),
            "update_time": datetime.utcnow()
        }
        result = await users_col.insert_one(user_data)
        user_data["_id"] = result.inserted_id

    return {
        "nonce": nonce,
        "message": message,
        "expires_in": NONCE_EXPIRY_MINUTES * 60
    }


async def wallet_login(request: WalletLoginRequest) -> WalletLoginResponse:
    """
    Handle wallet login/registration with nonce verification
    
    :param request: Wallet login request containing wallet address, signature, and chain type
    :return: Login response with tokens and user information
    """
    try:
        # Verify signature
        if not request.signature:
            raise CustomAgentException(message="Signature is required")

        # Get stored nonce data from Redis
        nonce_key = get_nonce_key(request.wallet_address)
        stored_nonce_data = REDIS.get_value(nonce_key)

        if not stored_nonce_data:
            raise CustomAgentException(message="Nonce not found or expired. Please request a new one.")

        nonce_data = json.loads(stored_nonce_data)
        nonce = nonce_data["nonce"]

        # Get chain type (default to ethereum if not provided)
        chain_type = request.chain_type or ChainType.ETHEREUM

        # Verify signature based on chain type
        message = get_message_to_sign(request.wallet_address, nonce)
        if not verify_signature(message, request.signature, request.wallet_address, chain_type):
            raise CustomAgentException(message="Invalid signature")

        # Delete used nonce from Redis
        REDIS.delete_key(nonce_key)

        # Get or create user with chain type
        user = await get_or_create_wallet_user(request.wallet_address, chain_type)

        # Set is_new_user flag - check if user was just created (no create_time or very recent)
        is_new_user = not user.get("create_time") or (datetime.utcnow() - user.get("create_time")).total_seconds() < 60

        # Update create_time if this is first login
        if not user.get("create_time"):
            await users_col.update_one(
                {"_id": user["_id"]},
                {"$set": {"create_time": datetime.utcnow()}}
            )

        # Generate token pair with chain type
        access_token, refresh_token = generate_token_pair(
            user_id=str(user["_id"]),
            username=user["username"],
            tenant_id=user.get("tenant_id"),
            wallet_address=user.get("wallet_address"),
            chain_type=user.get("chain_type")
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                'id': str(user["_id"]),
                'username': user["username"],
                'wallet_address': user.get("wallet_address"),
                'chain_type': user.get("chain_type"),
                'email': user.get("email")
            },
            "is_new_user": is_new_user,
            "access_token_expires_in": SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # convert to seconds
            "refresh_token_expires_in": SETTINGS.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # convert to seconds
        }

    except Exception as e:
        logger.error(f"Error in wallet login: {e}", exc_info=True)
        raise e


async def get_or_create_wallet_user(wallet_address: str,
                                    chain_type: Union[ChainType, str] = ChainType.ETHEREUM) -> dict:
    """
    Get existing user by wallet address or create a new one
    
    :param wallet_address: Wallet address
    :param chain_type: Blockchain type (ChainType enum or string)
    :return: User document
    """
    # Convert string to enum if needed
    if isinstance(chain_type, str):
        try:
            chain_type = ChainType(chain_type.lower())
        except ValueError:
            logger.warning(f"Unsupported chain type: {chain_type}, using default: {ChainType.ETHEREUM}")
            chain_type = ChainType.ETHEREUM

    # Convert enum to string for database storage
    chain_type_str = chain_type.value

    # Check if user exists
    user = await users_col.find_one({"wallet_address": wallet_address})

    if not user:
        # Create temporary user entry with generated username
        temp_username = f"wallet_{wallet_address[-8:]}"

        # Check if the generated username exists
        existing_user = await users_col.find_one({"username": temp_username})
        if existing_user:
            temp_username = f"wallet_{wallet_address[-8:]}_{uuid.uuid4().hex[:4]}"

        # Create new user with tenant_id
        tenant_id = str(uuid.uuid4())
        user_data = {
            "username": temp_username,
            "wallet_address": wallet_address,
            "chain_type": chain_type_str,
            "tenant_id": tenant_id,
            "create_time": datetime.utcnow(),
            "update_time": datetime.utcnow()
        }
        result = await users_col.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        user = user_data
    elif user.get("chain_type") != chain_type_str:
        # Update chain_type if it has changed
        await users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"chain_type": chain_type_str, "update_time": datetime.utcnow()}}
        )
        user["chain_type"] = chain_type_str
        user["update_time"] = datetime.utcnow()

    return user


async def refresh_token(refresh_token: str) -> TokenResponse:
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        raise CustomAgentException(message="Invalid or expired refresh token")

    # Get user info
    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise CustomAgentException(message="User not found")

    # Generate new token pair
    access_token, new_refresh_token = generate_token_pair(
        user_id=str(user["_id"]),
        username=user["username"],
        tenant_id=user.get("tenant_id"),
        wallet_address=user.get("wallet_address")
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "access_token_expires_in": SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # convert to seconds
        "refresh_token_expires_in": SETTINGS.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # convert to seconds
        "user": {
            'id': str(user["_id"]),
            'username': user["username"],
            'wallet_address': user.get("wallet_address"),
            'chain_type': user.get("chain_type"),
            'email': user.get("email")
        }
    }

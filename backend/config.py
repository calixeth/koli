from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ['.env', '../.env', '../../.env', '../../../.env']
        env_file_encoding = 'utf-8'
        extra = 'ignore'

    HOST: str = "0.0.0.0"
    PORT: int = 8080
    WORKERS: int = 1
    OPENAI_API_KEY: str = "<KEY>"
    PROMPT_KEY_ELEMENTS_APPEND: str = ""
    APP_NAME: str = "AgentServer"
    MONGO_STR: str = ""
    MONGO_DB: str = "agent-server"
    TWITTER241 = ""
    TWITTER241_HOST = ""
    TWITTER241_KEY = ""
    XAPI_IO_HOST = ""
    XAPI_IO_API_KEY = ""
    AWS_ACCESS_KEY = ""
    AWS_SECRET_KEY = ""
    OPENAI_IMAGE_API_KEY = ""
    PROXY_OPENAI_API_KEY = ""
    PROXY_OPENAI_BASE_URL = ""
    PROXY_GROK_API_KEY = ""
    PROXY_GROK_BASE_URL = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = None
    REDIS_SSL: bool = False
    REDIS_DB: int = 0
    REDIS_PREFIX: str = "default"
    IMAGE_TO_VIDEO_V2: str = ""
    IMAGE_TO_VIDEO_V3: str = ""
    IMAGE_TO_IMAGE_V3: str = ""
    GEN_T_URL_DANCE: str = ""
    GEN_T_URL_SING: str = ""
    FA_KEY: str = ""
    
    # TTS Provider Configuration
    TTS_PROVIDER: str = "voice_clone"  # "openai" or "voice_clone"
    VOICE_APPLICATION_ID: str = ""
    VOICE_APPLICATION_CLONE: str = ""
    VOICE_APPLICATION_MUSIC: str = ""

    JWT_SECRET: str = ""
    JWT_EXPIRATION_TIME: int = 1  # default one day
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12 * 30  # default 30 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 60  # default 60 days
    TEST_TOKEN = ""
    GEN_T_URL: str = ""
    X_APP_CLIENT_ID: str = ""
    X_APP_CLIENT_SECRET: str = ""
    X_APP_REDIRECT_URI: str = ""
    APP_HOME_URI: str = ""


SETTINGS = Settings()

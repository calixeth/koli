import base64
import logging
from abc import ABC, abstractmethod
from typing import Optional

import aiohttp
import fal_client
import openai

from config import SETTINGS


class BaseTTSClient(ABC):
    """Abstract base class for TTS clients"""

    @abstractmethod
    async def text_to_speech(
            self,
            text: str,
            voice: str = "alloy",
            model: str = "tts-1",
            response_format: str = "mp3",
            speed: float = 1.0,
            **kwargs
    ) -> Optional[bytes]:
        """Convert text to speech"""
        pass

    @abstractmethod
    async def text_to_speech_base64(
            self,
            text: str,
            voice: str = "alloy",
            model: str = "tts-1",
            response_format: str = "mp3",
            speed: float = 1.0,
            **kwargs
    ) -> Optional[str]:
        """Convert text to speech and return as base64"""
        pass


class OpenAITTSClient(BaseTTSClient):
    """OpenAI TTS client implementation"""

    def __init__(self):
        self.client = openai.AsyncClient(
            api_key=SETTINGS.OPENAI_API_KEY,
        )

    async def text_to_speech(
            self,
            text: str,
            voice: str = "alloy",
            model: str = "tts-1",
            response_format: str = "mp3",
            speed: float = 1.0,
            **kwargs
    ) -> Optional[bytes]:
        """
        Convert text to speech using OpenAI's TTS API
        
        Args:
            text: The text to convert to speech
            voice: The voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: The TTS model to use (tts-1, tts-1-hd)
            response_format: The audio format (mp3, opus, aac, flac)
            speed: The speed of the speech (0.25 to 4.0)
            **kwargs: Additional parameters (voice_id, audio_url, etc.)
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            logging.info(f"M Converting text to speech with OpenAI: {text[:50]}...")

            # Create arguments dict for OpenAI API call
            api_args = {
                "model": model,
                "voice": voice,
                "input": text,
                "response_format": response_format,
                "speed": speed
            }

            # Add any additional parameters that OpenAI might support
            # Note: OpenAI TTS doesn't support voice_id or audio_url, but we keep the interface flexible
            for key, value in kwargs.items():
                if key in ["voice_id", "audio_url"]:
                    logging.info(f"OpenAI TTS doesn't support {key}, ignoring: {value}")
                else:
                    api_args[key] = value

            response = await self.client.audio.speech.create(**api_args)

            if response:
                audio_data = response.content
                logging.info(f"M OpenAI TTS conversion successful, audio size: {len(audio_data)} bytes")
                return audio_data
            else:
                logging.error("M OpenAI TTS conversion failed: no response")
                return None

        except Exception as e:
            logging.error(f"M OpenAI TTS conversion error: {e}", exc_info=True)
            return None

    async def text_to_speech_base64(
            self,
            text: str,
            voice: str = "alloy",
            model: str = "tts-1",
            response_format: str = "mp3",
            speed: float = 1.0,
            **kwargs
    ) -> Optional[str]:
        """
        Convert text to speech and return as base64 encoded string
        
        Args:
            text: The text to convert to speech
            voice: The voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: The TTS model to use (tts-1, tts-1-hd)
            response_format: The audio format (mp3, opus, aac, flac)
            speed: The speed of the speech (0.25 to 4.0)
            **kwargs: Additional parameters (voice_id, audio_url, etc.)
            
        Returns:
            Base64 encoded audio data as string, or None if failed
        """
        try:
            audio_data = await self.text_to_speech(text, voice, model, response_format, speed, **kwargs)
            if audio_data:
                base64_audio = base64.b64encode(audio_data).decode('utf-8')
                logging.info(f"OpenAI TTS base64 conversion successful")
                return base64_audio
            return None
        except Exception as e:
            logging.error(f"OpenAI TTS base64 conversion error: {e}", exc_info=True)
            return None


class VoiceCloneTTSClient(BaseTTSClient):
    """Voice cloning TTS client implementation"""

    def __init__(self):
        pass

    async def text_to_speech(
            self,
            text: str,
            voice: str = "alloy",  # This will be ignored for voice clone, using cloned voice
            model: str = "speech-02-hd",  # Voice clone model options
            response_format: str = "mp3",
            speed: float = 1.0,
            **kwargs
    ) -> Optional[bytes]:
        """
        Convert text to speech using voice cloning API
        
        Args:
            text: The text to convert to speech
            voice: Ignored for voice clone (using cloned voice)
            model: The TTS model to use (speech-02-hd, speech-02-turbo, speech-01-hd, speech-01-turbo)
            response_format: The audio format (mp3, pcm, flac)
            speed: The speed of the speech (0.5 to 2.0)
            **kwargs: Additional parameters like voice_id, audio_url, etc.
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:

            arguments = {}
            if text:
                logging.info(f"M Converting text to speech with voice cloning: {text[:50]}...")
                arguments["text"] = text
            if kwargs.get("voice_id"):
                arguments.update({
                    "voice_setting": {
                        "voice_id": kwargs.get("voice_id"),
                    }
                })
            if kwargs.get("audio_url"):
                arguments.update({"audio_url": kwargs.get("audio_url")})
            if kwargs.get("prompt"):
                logging.info(f"Converting prompt to speech with voice cloning: {kwargs.get("prompt")[:50]}...")
                arguments.update({"prompt": kwargs.get("prompt")})
            if kwargs.get("reference_audio_url"):
                arguments.update({"reference_audio_url": kwargs.get("reference_audio_url")})
            voice_application = SETTINGS.VOICE_APPLICATION_ID
            if kwargs.get("voice_application"):
                voice_application = kwargs.get("voice_application")
            handler = await fal_client.submit_async(
                voice_application,
                arguments=arguments,
            )

            result = await handler.get()
            async with aiohttp.ClientSession() as session:
                if 'audio' in result and 'url' in result['audio']:
                    # Download the audio file
                    audio_url = result['audio']['url']
                    async with session.get(audio_url) as audio_response:
                        if audio_response.status == 200:
                            audio_data = await audio_response.read()
                            logging.info(f"Voice clone TTS conversion successful, audio size: {len(audio_data)} bytes")
                            return audio_data

        except Exception as e:
            logging.error(f"Voice clone TTS conversion error: {e}", exc_info=True)
            return None

    async def text_to_speech_base64(
            self,
            text: str,
            voice: str = "alloy",
            model: str = "speech-02-hd",
            response_format: str = "mp3",
            speed: float = 1.0,
            **kwargs
    ) -> Optional[str]:
        """
        Convert text to speech and return as base64 encoded string
        
        Args:
            text: The text to convert to speech
            voice: Ignored for voice clone (using cloned voice)
            model: The TTS model to use
            response_format: The audio format
            speed: The speed of the speech
            **kwargs: Additional parameters like voice_id, audio_url, etc.
            
        Returns:
            Base64 encoded audio data as string, or None if failed
        """
        try:
            audio_data = await self.text_to_speech(text, voice, model, response_format, speed, **kwargs)
            if audio_data:
                base64_audio = base64.b64encode(audio_data).decode('utf-8')
                logging.info(f"Voice clone TTS base64 conversion successful")
                return base64_audio
            return None
        except Exception as e:
            logging.error(f"Voice clone TTS base64 conversion error: {e}", exc_info=True)
            return None


class TTSClientFactory:
    """Factory class to create TTS clients based on configuration"""

    @staticmethod
    def create_client() -> BaseTTSClient:
        """Create TTS client based on TTS_PROVIDER environment variable"""
        provider = SETTINGS.TTS_PROVIDER.lower()

        if provider == "voice_clone":
            if not SETTINGS.FA_KEY:
                logging.warning("VOICE_CLONE_API_KEY not set, falling back to OpenAI")
                return OpenAITTSClient()
            return VoiceCloneTTSClient()
        elif provider == "openai":
            if not SETTINGS.OPENAI_API_KEY:
                logging.error("OPENAI_API_KEY is required for OpenAI TTS")
                raise ValueError("OPENAI_API_KEY is required for OpenAI TTS")
            return OpenAITTSClient()
        else:
            logging.warning(f"Unknown TTS provider: {provider}, falling back to OpenAI")
            return OpenAITTSClient()


class TTSClient:
    """Main TTS client that delegates to the appropriate provider"""

    def __init__(self):
        self._client = TTSClientFactory.create_client()

    async def text_to_speech(
            self,
            text: str,
            voice: str = None,
            model: str = None,
            response_format: str = None,
            speed: float = 1.0,
            **kwargs
    ) -> Optional[bytes]:
        """Delegate to the appropriate TTS client"""
        return await self._client.text_to_speech(text, voice, model, response_format, speed, **kwargs)

    async def text_to_speech_base64(
            self,
            text: str,
            voice: str = None,
            model: str = None,
            response_format: str = None,
            speed: float = 1.0,
            **kwargs
    ) -> Optional[str]:
        """Delegate to the appropriate TTS client"""
        return await self._client.text_to_speech_base64(text, voice, model, response_format, speed, **kwargs)

    async def call_language_model(
            self,
            prompt: str,
            model: str = "gpt-4o",
            max_tokens: int = 10000,
            temperature: float = 0.7,
            system_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Call language model with prompt and optional parameters
        
        Args:
            prompt: The input prompt for the language model
            model: The language model to use (gpt-4o-mini, gpt-4o, gpt-3.5-turbo, etc.)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 to 2.0)
            system_message: Optional system message to set context
            
        Returns:
            Generated text response, or None if failed
        """
        try:
            logging.info(f"Calling language model {model} with prompt: {prompt[:50]}...")

            # For language model calls, we still use OpenAI
            client = openai.AsyncClient(api_key=SETTINGS.OPENAI_API_KEY)

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            if response and response.choices:
                generated_text = response.choices[0].message.content
                logging.info(f"Language model response successful, length: {len(generated_text)}")
                return generated_text
            else:
                logging.error("Language model call failed: no response")
                return None

        except Exception as e:
            logging.error(f"Language model call error: {e}", exc_info=True)
            return None

    async def call_language_model_with_audio(
            self,
            prompt: str,
            audio_data: bytes,
            model: str = "gpt-4o",
            max_tokens: int = 10000,
            temperature: float = 0.7,
            system_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Call language model with prompt and audio input
        
        Args:
            prompt: The text prompt for the language model
            audio_data: Audio data as bytes
            model: The language model to use (gpt-4o-mini, gpt-4o, etc.)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 to 2.0)
            system_message: Optional system message to set context
            
        Returns:
            Generated text response, or None if failed
        """
        try:
            logging.info(f"Calling language model {model} with audio input, prompt: {prompt[:50]}...")

            # For language model calls with audio, we still use OpenAI
            client = openai.AsyncClient(api_key=SETTINGS.OPENAI_API_KEY)

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})

            # Add audio message
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "audio",
                        "audio": {
                            "data": audio_base64,
                            "type": "audio/mpeg"  # Adjust based on your audio format
                        }
                    }
                ]
            })

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            if response and response.choices:
                generated_text = response.choices[0].message.content
                logging.info(f"Language model with audio response successful, length: {len(generated_text)}")
                return generated_text
            else:
                logging.error("Language model with audio call failed: no response")
                return None

        except Exception as e:
            logging.error(f"Language model with audio call error: {e}", exc_info=True)
            return None


# Global TTS client instance
tts_client = TTSClient()


async def text_to_speech_svc(
        text: str,
        voice: str = None,
        model: str = None,
        response_format: str = None,
        speed: float = 1.0,
        **kwargs
) -> Optional[bytes]:
    """
    Service function for text-to-speech conversion
    
    Args:
        text: The text to convert to speech
        voice: The voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: The TTS model to use (tts-1, tts-1-hd)
        response_format: The audio format (mp3, opus, aac, flac)
        speed: The speed of the speech (0.25 to 4.0)
        **kwargs: Additional parameters like voice_id, audio_url, etc.
        
    Returns:
        Audio data as bytes, or None if failed
    """
    return await tts_client.text_to_speech(text, voice, model, response_format, speed, **kwargs)


async def text_to_speech_base64_svc(
        text: str,
        voice: str = None,
        model: str = None,
        response_format: str = None,
        speed: float = 1.0,
        **kwargs
) -> Optional[str]:
    """
    Service function for text-to-speech conversion returning base64
    
    Args:
        text: The text to convert to speech
        voice: The voice to use (alloy, echo, fable, onyx, nova, shimmer)
        model: The TTS model to use (tts-1, tts-1-hd)
        response_format: The audio format (mp3, opus, aac, flac)
        speed: The speed of the speech (0.25 to 4.0)
        **kwargs: Additional parameters like voice_id, audio_url, etc.
        
    Returns:
        Base64 encoded audio data as string, or None if failed
    """
    return await tts_client.text_to_speech_base64(text, voice, model, response_format, speed, **kwargs)


async def call_model(
        prompt: str,
        model: str = "gpt-4o",
        max_tokens: int = 15000,
        temperature: float = 0.7,
        system_message: Optional[str] = None
) -> Optional[str]:
    """
    Service function for language model calls
    
    Args:
        prompt: The input prompt for the language model
        model: The language model to use (gpt-4o-mini, gpt-4o, gpt-3.5-turbo, etc.)
        max_tokens: Maximum number of tokens to generate
        temperature: Controls randomness (0.0 to 2.0)
        system_message: Optional system message to set context
        
    Returns:
        Generated text response, or None if failed
    """
    return await tts_client.call_language_model(prompt, model, max_tokens, temperature, system_message)


async def call_model_with_audio(
        prompt: str,
        audio_data: bytes,
        model: str = "gpt-4o",
        max_tokens: int = 15000,
        temperature: float = 0.7,
        system_message: Optional[str] = None
) -> Optional[str]:
    """
    Service function for language model calls with audio input
    
    Args:
        prompt: The text prompt for the language model
        audio_data: Audio data as bytes
        model: The language model to use (gpt-4o-mini, gpt-4o, etc.)
        max_tokens: Maximum number of tokens to generate
        temperature: Controls randomness (0.0 to 2.0)
        system_message: Optional system message to set context
        
    Returns:
        Generated text response, or None if failed
    """
    return await tts_client.call_language_model_with_audio(prompt, audio_data, model, max_tokens, temperature,
                                                           system_message)

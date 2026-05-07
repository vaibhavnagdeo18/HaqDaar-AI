import aiohttp
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class SarvamService:
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.base_url = settings.SARVAM_BASE_URL.rstrip('/')
        self.headers = {
            "api-subscription-key": self.api_key
        }

    async def transcribe_voice(self, audio_bytes: bytes, language_hint: str = "hi-IN") -> str:
        """
        Transcribe audio bytes using Sarvam STT API.
        """
        url = f"{self.base_url}/speech-to-text"
        
        # Sarvam usually expects multipart/form-data for files
        data = aiohttp.FormData()
        data.add_field('file', audio_bytes, filename='audio.webm', content_type='audio/webm')
        data.add_field('language_code', language_hint)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=self.headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("transcript", "")
                    else:
                        error_text = await resp.text()
                        logger.error(f"Sarvam STT Error {resp.status}: {error_text}")
                        return ""
        except Exception as e:
            logger.error(f"Error calling Sarvam STT: {e}")
            return ""

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text using Sarvam Translate API.
        """
        if not text or source_lang == target_lang:
            return text
            
        lang_map = {
            "English": "en-IN",
            "Telugu": "te-IN",
            "Hindi": "hi-IN",
            "Tamil": "ta-IN",
            "Kannada": "kn-IN"
        }
        
        # Resolve mapped codes, fallback to original if not in map
        source_code = lang_map.get(source_lang, source_lang)
        target_code = lang_map.get(target_lang, target_lang)
            
        url = f"{self.base_url}/translate"
        payload = {
            "input": text,
            "source_language_code": source_code,
            "target_language_code": target_code,
            "speaker_gender": "Female"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("translated_text", text)
                    else:
                        error_text = await resp.text()
                        logger.error(f"Sarvam Translate Error {resp.status}: {error_text}")
                        return text
        except Exception as e:
            logger.error(f"Error calling Sarvam Translate: {e}")
            return text

    async def text_to_speech(self, text: str, language: str) -> bytes:
        """
        Convert text to speech using Sarvam TTS API.
        Returns audio bytes (base64 decoded).
        """
        url = f"{self.base_url}/text-to-speech"
        payload = {
            "inputs": [text],
            "target_language_code": language,
            "speaker": "vidya",
            "model": "bulbul:v2"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        # Sarvam usually returns a list of base64 strings in "audios"
                        audios = result.get("audios", [])
                        if audios:
                            import base64
                            return base64.b64decode(audios[0])
                        return b""
                    else:
                        error_text = await resp.text()
                        logger.error(f"Sarvam TTS Error {resp.status}: {error_text}")
                        return b""
        except Exception as e:
            logger.error(f"Error calling Sarvam TTS: {e}")
            return b""

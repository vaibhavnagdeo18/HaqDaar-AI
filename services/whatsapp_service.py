import aiohttp
import io
import logging
from typing import List
from core.config import settings
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        self.media_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/media"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def handle_incoming(self, webhook_payload: dict) -> None:
        """Entry point for all incoming WhatsApp messages."""
        pass

    async def _send_request(self, payload: dict) -> dict:
        """Helper to send the HTTP request to Meta API"""
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload, headers=self.headers) as resp:
                result = await resp.json()
                if resp.status not in [200, 201]:
                    logger.error(f"WhatsApp API Error {resp.status}: {result}")
                else:
                    logger.info(f"WhatsApp API Success: Message sent to {payload.get('to')}")
                return result

    async def download_media(self, media_id: str) -> bytes:
        """Download media from WhatsApp using media_id"""
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        async with aiohttp.ClientSession() as session:
            # 1. Get media URL
            async with session.get(url, headers={"Authorization": f"Bearer {self.token}"}) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to get media URL for {media_id}")
                    return b""
                data = await resp.json()
                download_url = data.get("url")
            
            if not download_url:
                return b""
                
            # 2. Download the binary
            async with session.get(download_url, headers={"Authorization": f"Bearer {self.token}"}) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.error(f"Failed to download media binary from {download_url}")
                return b""

    async def upload_media(self, media_bytes: bytes, mime_type: str = "audio/ogg", filename: str = "audio.ogg") -> str:
        """Upload media bytes to WhatsApp and return media_id"""
        data = aiohttp.FormData()
        data.add_field('file', media_bytes, filename=filename, content_type=mime_type)
        data.add_field('messaging_product', 'whatsapp')
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.media_url, data=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("id")
                else:
                    error_text = await resp.text()
                    logger.error(f"WhatsApp Media Upload Error: {error_text}")
                    return None

    async def send_text(self, to: str, message: str) -> None:
        """Send text message."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        await self._send_request(payload)

    async def send_voice(self, to: str, audio_bytes: bytes) -> None:
        """
        Send voice note. 
        Converts WAV bytes from Sarvam to OGG Opus using pydub before uploading to Meta.
        """
        logger.info(f"Converting and uploading voice note to Meta for {to}")
        
        try:
            # Convert WAV to OGG Opus using pydub
            audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
            ogg_io = io.BytesIO()
            # WhatsApp requires ogg opus for voice notes
            audio.export(ogg_io, format="ogg", codec="libopus")
            processed_bytes = ogg_io.getvalue()
            
            media_id = await self.upload_media(processed_bytes, mime_type="audio/ogg", filename="audio.ogg")
            
            if media_id:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "audio",
                    "audio": {"id": media_id}
                }
                await self._send_request(payload)
            else:
                logger.error("Failed to upload audio bytes for voice note.")
        except Exception as e:
            logger.error(f"Voice note conversion/upload failed: {e}")
            # Skip voice note silently as per instructions
            return

    async def send_document(self, to: str, pdf_bytes: bytes, filename: str, caption: str = None) -> None:
        """Send generated PDF form back to family."""
        logger.info(f"Sending document {filename} to {to}")
        media_id = await self.upload_media(pdf_bytes, mime_type="application/pdf", filename=filename)
        
        if media_id:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "document",
                "document": {
                    "id": media_id,
                    "filename": filename
                }
            }
            if caption:
                payload["document"]["caption"] = caption
            await self._send_request(payload)
        else:
            logger.error(f"Failed to upload document {filename}")

    async def send_interactive(self, to: str, body: str, buttons: List[str]) -> None:
        """Send message with quick reply buttons."""
        pass

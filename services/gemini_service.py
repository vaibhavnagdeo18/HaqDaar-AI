import google.generativeai as genai
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Using Gemini 1.5 Flash as standard for generic tasks
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.vision_model = genai.GenerativeModel('gemini-2.5-flash') # Or gemini-1.5-pro for complex OCR

    async def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        """
        Generic text generation wrapper.
        """
        try:
            if system_instruction:
                model = genai.GenerativeModel(
                    'gemini-2.5-flash',
                    system_instruction=system_instruction
                )
            else:
                model = self.model
                
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating text from Gemini: {e}")
            raise

    async def process_image(self, image_path: str, prompt: str) -> str:
        """
        Process images (documents, denial notices) using Gemini Vision.
        Supports JPEG/PNG directly and PDF (first page converted to image).
        """
        try:
            import PIL.Image
            if image_path.lower().endswith(".pdf"):
                from pypdf import PdfReader
                from io import BytesIO
                reader = PdfReader(image_path)
                if not reader.pages:
                    raise ValueError("Empty PDF")
                # Extract images from first page; fall back to blank canvas
                images = list(reader.pages[0].images)
                if images:
                    img = PIL.Image.open(BytesIO(images[0].data))
                else:
                    img = PIL.Image.new("RGB", (800, 600), color="white")
            else:
                img = PIL.Image.open(image_path)
            response = await self.vision_model.generate_content_async([prompt, img])
            return response.text
        except Exception as e:
            logger.error(f"Error processing image with Gemini: {e}")
            raise

"""
Voice transcription service using OpenAI Whisper.
Handles audio download from Telegram and transcription.
"""

import logging
import asyncio
import requests
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def transcribe_voice(file_url: str, language: str = "ru") -> Optional[str]:
    """
    Transcribe audio file using OpenAI Whisper.

    Downloads audio from Telegram URL, saves temporarily, and transcribes.

    Args:
        file_url: URL to audio file (Telegram file URL)
        language: Language code (default: "ru" for Russian)

    Returns:
        str: Transcribed text, or None if error
    """
    tmp_path = None
    try:
        # Download audio in background thread
        def _download():
            resp = requests.get(file_url, timeout=60)
            resp.raise_for_status()
            return resp.content

        logger.info(f"Downloading audio from Telegram")
        audio_bytes = await asyncio.to_thread(_download)

        # Save to temporary file
        tmp_path = Path("data/tg_voice.ogg")
        tmp_path.parent.mkdir(parents=True, exist_ok=True)

        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

        logger.info(f"Saved audio to {tmp_path}, size: {len(audio_bytes)} bytes")

        # Transcribe with OpenAI
        try:
            with open(tmp_path, "rb") as f:
                try:
                    # Try fast and accurate variant
                    logger.info("Transcribing with gpt-4o-mini-transcribe")
                    resp = await client.audio.transcriptions.create(
                        model="gpt-4o-mini-transcribe",
                        file=f,
                        language=language,
                    )
                except Exception as e:
                    logger.warning(f"gpt-4o-mini-transcribe failed: {e}, falling back to whisper-1")
                    # Fallback to classic whisper-1
                    f.seek(0)
                    resp = await client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        language=language,
                    )
        finally:
            # Clean up temporary file
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink(missing_ok=True)
                    logger.debug(f"Cleaned up temporary file: {tmp_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")

        logger.info(f"Successfully transcribed audio, text length: {len(resp.text)}")
        return resp.text

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None

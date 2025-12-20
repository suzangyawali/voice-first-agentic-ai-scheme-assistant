"""
Hindi Text-to-Speech (TTS)
Using gTTS
Cross-platform, blocking-safe
"""

import os
import platform
import subprocess
import logging
from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)


class HindiTTS:
    def __init__(self):
        self.language = "hi"
        logger.info("TTS initialized (Hindi)")

    def generate_audio(self, text: str) -> str:
        """
        Generate audio file and return path (synchronous)
        Used by web server for returning audio to browser
        """
        try:
            from gtts import gTTS

            logger.info("[TTS] Generating audio: %s...", text[:50])

            with NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                audio_path = tmp.name

            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(audio_path)

            logger.info("[TTS] Audio saved: %s", audio_path)
            return audio_path

        except Exception as e:
            logger.error("[TTS] Generation failed: %s", e, exc_info=True)
            return None

    async def speak(self, text: str) -> bool:
        """
        Generate and play audio (async, for console)
        """
        try:
            from gtts import gTTS

            logger.info("[TTS] Speaking: %s...", text[:50])
            print(f"🎙️ Agent: {text}")

            with NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                audio_path = tmp.name

            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(audio_path)

            system = platform.system()

            try:
                if system == "Darwin":  # macOS
                    subprocess.run(["afplay", audio_path], check=True)

                elif system == "Linux":
                    subprocess.run(
                        ["ffplay", "-nodisp", "-autoexit", audio_path],
                        stderr=subprocess.DEVNULL,
                        check=True
                    )

                elif system == "Windows":
                    subprocess.run(
                        ["powershell", "-c",
                         f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()"],
                        check=True
                    )

                else:
                    logger.warning("Unsupported OS for audio playback")

            finally:
                try:
                    os.remove(audio_path)
                except Exception:
                    pass

            return True

        except Exception:
            logger.exception("[TTS] Playback failed")
            print(f"🎙️ Agent: {text}")
            return False

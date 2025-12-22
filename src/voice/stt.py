"""
Hindi Speech-to-Text (STT)
Using AssemblyAI for reliable Hindi transcription
No system dependencies (ffmpeg, Whisper) required
"""

import os
import logging
import numpy as np
import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

logger = logging.getLogger(__name__)


class HindiSTT:
    def __init__(self, model: str = "small", debug_audio: bool = True):
        """
        Use AssemblyAI for reliable Hindi transcription.
        
        Args:
            model: Ignored (kept for compatibility)
            debug_audio: Save raw audio files for quality inspection
        """
        self.language = "hi"
        self.debug_audio = debug_audio
        
        # Create audio debug directory
        self.audio_debug_dir = Path("audio_debug")
        if self.debug_audio:
            self.audio_debug_dir.mkdir(exist_ok=True)
            logger.info(f"[STT] Audio debug directory: {self.audio_debug_dir.absolute()}")
        
        # Import AssemblyAI STT
        from voice.assemblyai_stt import AssemblyAISTT
        self._assemblyai_stt = AssemblyAISTT()
        
        logger.info("[STT] AssemblyAI STT initialized (Hindi transcription)")

    def _load_model(self):
        # No model loading needed for AssemblyAI (API-based)
        pass



    async def listen(
        self,
        max_duration: float = 10.0,
        silence_duration: float = 1.5,
        silence_threshold: float = 0.01
    ) -> Optional[str]:
        """
        Record microphone input and transcribe using AssemblyAI.
        
        Args:
            max_duration: Maximum recording duration in seconds
            silence_duration: Silence threshold to stop recording
            silence_threshold: Volume threshold for silence detection
        
        Returns:
            Transcribed text or None if transcription fails
        """
        return await self._assemblyai_stt.listen(max_duration)

    def get_audio_debug_report(self) -> str:
        """
        Generate a report of all recorded audio files for quality inspection.
        
        Returns:
            String containing file list and location
        """
        if not self.debug_audio or not self.audio_debug_dir.exists():
            return "Audio debug directory not found or debug_audio is disabled"
        
        audio_files = list(self.audio_debug_dir.glob("*.wav"))
        if not audio_files:
            return f"No audio files found in {self.audio_debug_dir.absolute()}"
        
        report = [
            "\n" + "="*70,
            "🎤 AUDIO DEBUG REPORT",
            "="*70,
            f"Location: {self.audio_debug_dir.absolute()}",
            f"Total recordings: {len(audio_files)}",
            "",
            "Files (newest first):",
            "-"*70,
        ]
        
        for audio_file in sorted(audio_files, reverse=True)[:10]:  # Show last 10
            file_size_kb = audio_file.stat().st_size / 1024
            report.append(f"  • {audio_file.name} ({file_size_kb:.1f} KB)")
        
        report.extend([
            "-"*70,
            "",
            "🔍 WHAT TO CHECK IN EACH FILE:",
            "  ✓ Can you clearly hear Hindi speech?",
            "  ✓ Is the volume normal (not too loud/soft)?",
            "  ✓ No clipping (distortion/crackling)?",
            "  ✓ No excessive silence at start/end?",
            "",
            "📊 Use: ffprobe, Audacity, or any audio player to inspect",
            "   Command: open audio_debug/ (on macOS)",
            "="*70 + "\n"
        ])
        
        return "\n".join(report)


class HindiTTS:
    """
    Hindi Text-to-Speech Engine using gTTS
    """

    def __init__(self):
        self.language = "hi"
        logger.info("TTS initialized (Hindi)")

    async def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Convert Hindi text to speech and play audio.

        Args:
            text: Hindi text to speak
            blocking: wait briefly after speaking

        Returns:
            Success status
        """
        try:
            from gtts import gTTS
            import platform

            logger.info("[TTS] Speaking: %s...", text[:40])
            print(f"🎙️ Agent: {text}")

            with NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                audio_path = tmp.name

            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(audio_path)

            system = platform.system()

            if system == "Darwin":       # macOS
                os.system(f"afplay {audio_path}")
            elif system == "Linux":
                os.system(f"ffplay -nodisp -autoexit {audio_path}")
            elif system == "Windows":
                os.system(f"mpg123 {audio_path}")
            else:
                logger.warning("Unsupported OS for audio playback: %s", system)

            if blocking:
                await asyncio.sleep(0.1)

            return True

        except Exception as e:
            logger.warning(
                "[TTS] Speech playback failed (%s); falling back to text output",
                e
            )
            print(f"🎙️ Agent: {text}")
            return True

        finally:
            try:
                if "audio_path" in locals() and os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass

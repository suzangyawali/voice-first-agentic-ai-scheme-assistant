"""
AssemblyAI Speech-to-Text (STT)
DEFENSIVE VERSION — works even with legacy callers
macOS-safe, crackle-free audio
"""

import os
import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class AssemblyAISTT:
    def __init__(self):
        self.api_key = os.environ.get("ASSEMBLYAI_API_KEY")
        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY not set")

        self.base_url = "https://api.assemblyai.com/v2"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        logger.info("[STT] AssemblyAI initialized")

    # --------------------------------------------------
    # TRANSCRIBE FILE
    # --------------------------------------------------
    def transcribe_file(self, file_path: str) -> Optional[str]:
        try:
            upload = requests.post(
                f"{self.base_url}/upload",
                headers={"Authorization": self.api_key},
                data=open(file_path, "rb"),
            )
            audio_url = upload.json()["upload_url"]

            job = requests.post(
                f"{self.base_url}/transcript",
                json={"audio_url": audio_url, "language_code": "hi"},
                headers=self.headers,
            ).json()

            tid = job["id"]

            while True:
                r = requests.get(
                    f"{self.base_url}/transcript/{tid}",
                    headers=self.headers,
                ).json()

                if r["status"] == "completed":
                    return r.get("text")
                if r["status"] == "error":
                    return None

                time.sleep(1)

        except Exception as e:
            logger.error(f"[STT] Transcription failed: {e}")
            return None

    # --------------------------------------------------
    # DEFENSIVE LISTEN (ACCEPTS ANY ARGUMENTS)
    # --------------------------------------------------
    async def listen(self, *args, **kwargs) -> Optional[str]:
        """
        Accepts:
          listen()
          listen(duration)
          listen(max_duration, silence_duration)
          listen(duration=...)

        This prevents crashes from old wrappers.
        """

        # Extract duration safely
        duration = 7.0
        if len(args) >= 1 and isinstance(args[0], (int, float)):
            duration = args[0]
        if "duration" in kwargs:
            duration = kwargs["duration"]
        if "max_duration" in kwargs:
            duration = kwargs["max_duration"]

        try:
            import sounddevice as sd
            import numpy as np
            import tempfile
            import wave
            import queue

            sr = 16000
            block = 1024
            q = queue.Queue()

            def cb(indata, frames, time_info, status):
                q.put(indata.copy())

            print("🎤 Prepare to speak...")
            time.sleep(0.6)
            print("🎤 Speak now (Hindi)...")

            frames = []
            with sd.InputStream(
                samplerate=sr,
                channels=1,
                dtype="float32",
                blocksize=block,
                callback=cb,
            ):
                for _ in range(int(duration * sr / block)):
                    frames.append(q.get())

            audio = np.concatenate(frames, axis=0)
            audio = np.clip(audio * 32767, -32768, 32767).astype("int16")

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name
                with wave.open(path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(audio.tobytes())

            return self.transcribe_file(path)

        except Exception as e:
            logger.error(f"[STT] Recording failed: {e}")
            return None

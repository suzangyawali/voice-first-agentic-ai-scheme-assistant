"""
AssemblyAI Speech-to-Text (STT)
Reliable Hindi transcription without system dependencies
"""

import os
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class AssemblyAISTT:
    """
    AssemblyAI-based STT for Hindi transcription
    Uses REST API for reliable, cloud-based transcription
    """
    
    def __init__(self):
        """Initialize AssemblyAI STT"""
        self.api_key = os.environ.get("ASSEMBLYAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "ASSEMBLYAI_API_KEY environment variable not set. "
                "Please set: export ASSEMBLYAI_API_KEY='your_key_here'"
            )
        
        self.base_url = "https://api.assemblyai.com/v2"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        logger.info("[STT] AssemblyAI initialized (Hindi transcription)")
    
    def transcribe_file(self, file_path: str) -> Optional[str]:
        """
        Transcribe a WAV/MP3 file using AssemblyAI
        
        Args:
            file_path: Path to audio file
        
        Returns:
            Transcribed text or None if transcription fails/is empty
        """
        try:
            # Step 1: Upload audio file
            logger.info(f"[STT] Uploading audio: {file_path}")
            upload_url = f"{self.base_url}/upload"
            
            with open(file_path, "rb") as f:
                upload_response = requests.post(
                    upload_url,
                    headers={"Authorization": self.api_key},
                    data=f
                )
            
            if upload_response.status_code != 200:
                logger.error(f"[STT] Upload failed: {upload_response.text}")
                return None
            
            audio_url = upload_response.json()["upload_url"]
            logger.info(f"[STT] Audio uploaded: {audio_url}")
            
            # Step 2: Submit transcription job
            logger.info("[STT] Submitting transcription job (language=hi)")
            transcript_url = f"{self.base_url}/transcript"
            
            payload = {
                "audio_url": audio_url,
                "language_code": "hi",  # Hindi
                "language_detection": False,  # Explicit language, no detection needed
            }
            
            transcript_response = requests.post(
                transcript_url,
                json=payload,
                headers=self.headers
            )
            
            if transcript_response.status_code != 200:
                logger.error(f"[STT] Transcription submission failed: {transcript_response.text}")
                return None
            
            transcript_id = transcript_response.json()["id"]
            logger.info(f"[STT] Transcription job submitted: {transcript_id}")
            
            # Step 3: Poll for completion
            logger.info("[STT] Waiting for transcription...")
            while True:
                status_response = requests.get(
                    f"{transcript_url}/{transcript_id}",
                    headers=self.headers
                )
                
                if status_response.status_code != 200:
                    logger.error(f"[STT] Status check failed: {status_response.text}")
                    return None
                
                result = status_response.json()
                status = result.get("status")
                
                if status == "completed":
                    text = result.get("text", "").strip()
                    
                    if not text:
                        logger.warning("[STT] Empty transcription returned")
                        return None
                    
                    logger.info(f"[STT] Transcribed: {text}")
                    return text
                
                elif status == "error":
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"[STT] Transcription error: {error_msg}")
                    return None
                
                # Still processing, wait a bit
                import time
                time.sleep(1)
        
        except FileNotFoundError:
            logger.error(f"[STT] Audio file not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"[STT] Transcription failed: {e}", exc_info=True)
            return None
    
    async def listen(self, max_duration: float = 10.0, silence_duration: float = 1.5) -> Optional[str]:
        """
        Record audio from microphone and transcribe using AssemblyAI
        
        Args:
            max_duration: Maximum recording duration in seconds
            silence_duration: Silence threshold to stop recording
        
        Returns:
            Transcribed text or None
        """
        try:
            import sounddevice as sd
            import numpy as np
            import wave
            import tempfile
            
            logger.info("[STT] Listening for Hindi audio...")
            
            # Record audio
            sample_rate = 16000
            chunk_duration = 0.1
            chunk_samples = int(sample_rate * chunk_duration)
            silence_threshold = 0.02
            silence_samples = int(sample_rate * silence_duration)
            
            frames = []
            silence_count = 0
            chunk_count = 0
            max_chunks = int(max_duration / chunk_duration)
            
            print("🎤 Listening... (speak in Hindi, clear your voice)")
            
            while chunk_count < max_chunks:
                chunk = sd.rec(
                    chunk_samples,
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    blocking=True
                )
                frames.append(chunk)
                chunk_count += 1
                
                # Check for silence
                volume = np.max(np.abs(chunk))
                if volume < silence_threshold:
                    silence_count += 1
                else:
                    silence_count = 0
                
                # Stop on sustained silence
                if silence_count >= silence_samples / chunk_samples:
                    logger.info("[STT] Silence detected, stopping recording")
                    break
            
            # Combine audio
            audio = np.concatenate(frames, axis=0)
            
            # Normalize
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val
            
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                with wave.open(tmp_path, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes((audio * 32767).astype(np.int16).tobytes())
                
                logger.info(f"[STT] Audio saved: {tmp_path}")
                
                # Transcribe
                text = self.transcribe_file(tmp_path)
                
                # Cleanup
                try:
                    os.remove(tmp_path)
                except:
                    pass
                
                return text
        
        except ImportError:
            logger.error("[STT] sounddevice not installed")
            return None
        except Exception as e:
            logger.error(f"[STT] Recording failed: {e}", exc_info=True)
            return None

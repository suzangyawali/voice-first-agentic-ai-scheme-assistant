"""
Browser-based Microphone Recording
Uses Web Audio API via Flask/HTML interface
Records audio from browser's microphone instead of system sounddevice
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
import base64
from datetime import datetime

logger = logging.getLogger(__name__)


class BrowserMicRecorder:
    """
    Handles browser microphone recording via Web Audio API
    Receives audio chunks from browser frontend
    Assembles and transcribes
    """
    
    def __init__(self):
        """Initialize browser recorder"""
        self.recording_data = None
        self.sample_rate = 16000
        self.audio_buffer = []
        self.recording_dir = Path("browser_recordings")
        self.recording_dir.mkdir(exist_ok=True)
        
        logger.info("[BROWSER_MIC] Browser microphone recorder initialized")
    
    def start_recording(self):
        """Start new recording session"""
        self.audio_buffer = []
        self.recording_data = {
            "timestamp": datetime.now().isoformat(),
            "chunks": []
        }
        logger.info("[BROWSER_MIC] Recording started from browser")
    
    def add_audio_chunk(self, chunk_base64: str):
        """
        Add audio chunk from browser
        
        Args:
            chunk_base64: Base64-encoded audio data from browser
        """
        try:
            # Decode base64 chunk
            chunk_bytes = base64.b64decode(chunk_base64)
            self.audio_buffer.append(chunk_bytes)
            self.recording_data["chunks"].append(chunk_base64)
            logger.debug(f"[BROWSER_MIC] Added chunk: {len(chunk_bytes)} bytes")
        except Exception as e:
            logger.error(f"[BROWSER_MIC] Failed to add chunk: {e}")
    
    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and save audio file
        
        Returns:
            Path to saved WAV file or None if failed
        """
        if not self.audio_buffer:
            logger.warning("[BROWSER_MIC] No audio chunks recorded")
            return None
        
        try:
            import wave
            import numpy as np
            
            # Combine chunks
            combined = b''.join(self.audio_buffer)
            
            # Convert to WAV format
            timestamp = int(datetime.now().timestamp() * 1000)
            wav_path = self.recording_dir / f"browser_recording_{timestamp}.wav"
            
            # Save as WAV (16-bit PCM, 16kHz, mono)
            with wave.open(str(wav_path), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(combined)
            
            logger.info(f"[BROWSER_MIC] Recording saved: {wav_path}")
            logger.info(f"[BROWSER_MIC] File size: {wav_path.stat().st_size / 1024:.1f} KB")
            
            self.audio_buffer = []
            return str(wav_path)
        
        except Exception as e:
            logger.error(f"[BROWSER_MIC] Failed to save recording: {e}", exc_info=True)
            return None


# HTML/JavaScript for browser recording
BROWSER_RECORDER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Voice Agent - Browser Microphone</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            background: rgba(0,0,0,0.3);
            padding: 30px;
            border-radius: 10px;
            text-align: center;
        }
        h1 { margin-top: 0; }
        .status {
            font-size: 18px;
            margin: 20px 0;
            padding: 10px;
            background: rgba(0,0,0,0.5);
            border-radius: 5px;
        }
        .status.recording {
            background: #ff4444;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        button {
            padding: 12px 30px;
            font-size: 16px;
            margin: 10px 5px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            background: white;
            color: #667eea;
            font-weight: bold;
            transition: all 0.3s;
        }
        button:hover { transform: scale(1.05); }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .transcript {
            background: rgba(0,0,0,0.5);
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            text-align: left;
            min-height: 60px;
        }
        .error {
            color: #ff6666;
        }
        .success {
            color: #66ff66;
        }
        .instruction {
            font-size: 14px;
            margin: 15px 0;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 Voice Agent</h1>
        <p class="instruction">सरकारी योजनाओं के लिए अपनी आवाज का प्रयोग करें</p>
        
        <div class="status" id="status">🎙️ Ready to record</div>
        
        <button id="startBtn" onclick="startRecording()">🎤 Start Recording</button>
        <button id="stopBtn" onclick="stopRecording()" disabled>⏹️ Stop Recording</button>
        <button id="submitBtn" onclick="submitAudio()" disabled>📤 Submit</button>
        
        <div class="transcript">
            <div id="output">Waiting for input...</div>
        </div>
    </div>

    <script>
        let mediaStream = null;
        let audioContext = null;
        let processor = null;
        let isRecording = false;
        let audioChunks = [];

        async function startRecording() {
            try {
                // Request browser microphone
                mediaStream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: false
                    }
                });
                
                // Setup Web Audio API
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaStreamSource(mediaStream);
                
                // Create processor for audio chunks
                processor = audioContext.createScriptProcessor(4096, 1, 1);
                source.connect(processor);
                processor.connect(audioContext.destination);
                
                audioChunks = [];
                isRecording = true;
                
                // Process audio chunks
                processor.onaudioprocess = (e) => {
                    const input = e.inputBuffer.getChannelData(0);
                    // Convert to 16-bit PCM
                    const pcm = new Int16Array(input.length);
                    for (let i = 0; i < input.length; i++) {
                        pcm[i] = Math.max(-1, Math.min(1, input[i])) < 0 
                            ? input[i] * 0x8000 
                            : input[i] * 0x7FFF;
                    }
                    audioChunks.push(pcm);
                };
                
                updateStatus("🔴 Recording...", true);
                document.getElementById("startBtn").disabled = true;
                document.getElementById("stopBtn").disabled = false;
                
            } catch (error) {
                updateOutput(`❌ Microphone access denied: ${error.message}`, "error");
                updateStatus("❌ Error accessing microphone", false);
            }
        }

        function stopRecording() {
            if (!isRecording) return;
            
            isRecording = false;
            mediaStream.getTracks().forEach(track => track.stop());
            processor.disconnect();
            audioContext.close();
            
            updateStatus("✅ Recording stopped", false);
            document.getElementById("startBtn").disabled = false;
            document.getElementById("stopBtn").disabled = true;
            document.getElementById("submitBtn").disabled = false;
            
            updateOutput(`📊 Captured ${audioChunks.length} audio chunks. Ready to submit.`);
        }

        function submitAudio() {
            if (audioChunks.length === 0) {
                updateOutput("❌ No audio recorded", "error");
                return;
            }
            
            // Convert chunks to WAV format
            const wavData = encodeWAV(audioChunks, 16000);
            
            // Send to backend
            fetch("/api/transcribe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    audio: btoa(String.fromCharCode.apply(null, new Uint8Array(wavData))),
                    sample_rate: 16000
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateOutput(`✅ Transcribed: ${data.text}`, "success");
                    updateOutput(`🤖 Agent: ${data.response}`);
                } else {
                    updateOutput(`❌ Error: ${data.error}`, "error");
                }
            })
            .catch(error => {
                updateOutput(`❌ Network error: ${error.message}`, "error");
            });
            
            document.getElementById("submitBtn").disabled = true;
        }

        function encodeWAV(chunks, sampleRate) {
            // Convert PCM chunks to WAV format
            const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
            const audioData = new Int16Array(length);
            let offset = 0;
            
            for (const chunk of chunks) {
                audioData.set(chunk, offset);
                offset += chunk.length;
            }
            
            const wavHeader = createWavHeader(audioData, sampleRate);
            return concatenateArrays(wavHeader, audioData.buffer);
        }

        function createWavHeader(audioData, sampleRate) {
            const channels = 1;
            const bitDepth = 16;
            const byteRate = sampleRate * channels * (bitDepth / 8);
            const blockAlign = channels * (bitDepth / 8);
            const dataSize = audioData.length * 2;
            
            const header = new ArrayBuffer(44);
            const view = new DataView(header);
            
            // "RIFF" chunk
            view.setUint8(0, 0x52); view.setUint8(1, 0x49); view.setUint8(2, 0x46); view.setUint8(3, 0x46);
            view.setUint32(4, 36 + dataSize, true);
            
            // "WAVE" format
            view.setUint8(8, 0x57); view.setUint8(9, 0x41); view.setUint8(10, 0x56); view.setUint8(11, 0x45);
            
            // "fmt " subchunk
            view.setUint8(12, 0x66); view.setUint8(13, 0x6d); view.setUint8(14, 0x74); view.setUint8(15, 0x20);
            view.setUint32(16, 16, true); // Subchunk1Size
            view.setUint16(20, 1, true); // PCM format
            view.setUint16(22, channels, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, byteRate, true);
            view.setUint16(32, blockAlign, true);
            view.setUint16(34, bitDepth, true);
            
            // "data" subchunk
            view.setUint8(36, 0x64); view.setUint8(37, 0x61); view.setUint8(38, 0x74); view.setUint8(39, 0x61);
            view.setUint32(40, dataSize, true);
            
            return header;
        }

        function concatenateArrays(a, b) {
            const result = new Uint8Array(a.byteLength + b.byteLength);
            result.set(new Uint8Array(a), 0);
            result.set(new Uint8Array(b), a.byteLength);
            return result;
        }

        function updateStatus(message, recording = false) {
            const status = document.getElementById("status");
            status.textContent = message;
            if (recording) {
                status.classList.add("recording");
            } else {
                status.classList.remove("recording");
            }
        }

        function updateOutput(message, className = "") {
            const output = document.getElementById("output");
            if (className) {
                output.className = className;
            }
            output.textContent = message;
        }
    </script>
</body>
</html>
"""


def get_browser_recorder_html() -> str:
    """Return HTML/JS for browser recorder interface"""
    return BROWSER_RECORDER_HTML

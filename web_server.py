"""
Browser-based Voice Agent Web Server
Full voice conversation loop with automatic STT/TTS
Agent speaks → Browser listens → User speaks → Process → Agent responds → repeat
"""

import os
import sys
import json
import logging
import base64
import tempfile
from pathlib import Path
from datetime import datetime

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from flask import Flask, render_template_string, request, jsonify, send_file
from dotenv import load_dotenv

# Load env
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import voice modules
try:
    from voice.assemblyai_stt import AssemblyAISTT
    from voice.tts import HindiTTS
    from graph import create_agent_graph
    from state.schema import AgentState
    from nodes.executor import is_low_quality_input
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Initialize Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Initialize components
logger.info("Initializing voice components...")
stt = AssemblyAISTT()
tts = HindiTTS()
agent_graph = create_agent_graph()

# Store conversation state (per session)
conversation_state = {}

logger.info("✅ Browser Voice Agent Server initialized")


# ==================== CONVERSATION ENDPOINTS ====================

@app.route('/api/start', methods=['GET'])
def start_conversation():
    """
    Start a new conversation
    Returns agent greeting message + audio
    """
    try:
        session_id = request.args.get('session_id', str(datetime.now().timestamp()))
        logger.info(f"[START] New conversation: {session_id}")
        
        # Reset conversation state for this session
        conversation_state[session_id] = {
            'turn_count': 0,
            'messages': [],
            'profile': {}
        }
        
        # Agent greeting
        greeting = "नमस्ते! मैं आपकी सरकारी योजनाओं में मदद के लिए यहाँ हूँ। कृपया बताइए आप क्या जानना चाहते हैं?"
        
        logger.info(f"[START] Agent greeting: {greeting}")
        
        # Generate audio
        logger.info("[START] Generating TTS audio for greeting...")
        audio_file = tts.generate_audio(greeting)
        
        # Note: Audio playback will be handled by the browser, not on server
        # This ensures proper audio context and speaker control
        
        # Read audio and encode to base64
        if audio_file:
            with open(audio_file, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode('utf-8')
            logger.info(f"[START] Audio generated: {len(audio_data)} bytes")
            
            try:
                os.remove(audio_file)
            except:
                pass
        else:
            audio_data = None
            logger.warning("[START] Failed to generate audio")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "text": greeting,
            "audio": audio_data,
            "listen": True
        })
    
    except Exception as e:
        logger.error(f"[START] Error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/voice', methods=['POST'])
def process_voice():
    """
    Process user voice input
    - Transcribe audio (STT)
    - Process through agent (Planner → Executor → Evaluator)
    - Generate response audio (TTS)
    
    Request:
    {
        "audio": "base64_encoded_wav",
        "session_id": "unique_session_id"
    }
    
    Response:
    {
        "success": true/false,
        "user_text": "transcribed_input",
        "agent_text": "agent_response",
        "audio": "base64_encoded_response_audio",
        "listen": true/false,  # Continue listening?
        "low_confidence": true/false
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'audio' not in data:
            return jsonify({
                "success": False,
                "error": "Missing audio data"
            }), 400
        
        session_id = data.get('session_id', 'default')
        
        # Ensure session exists
        if session_id not in conversation_state:
            conversation_state[session_id] = {
                'turn_count': 0,
                'messages': [],
                'profile': {}
            }
        
        logger.info(f"[VOICE] Processing turn {conversation_state[session_id]['turn_count'] + 1}")
        
        # ===== STEP 1: DECODE AUDIO =====
        try:
            audio_bytes = base64.b64decode(data['audio'])
            logger.info(f"[STT] Received audio: {len(audio_bytes)} bytes")
        except Exception as e:
            logger.error(f"[STT] Failed to decode audio: {e}")
            return jsonify({
                "success": False,
                "error": "Invalid audio data"
            }), 400
        
        # ===== STEP 2: SAVE AND TRANSCRIBE (STT) =====
        user_text = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            logger.info(f"[STT] Transcribing audio: {tmp_path}")
            user_text = stt.transcribe_file(tmp_path)
            
            if not user_text:
                logger.warning("[STT] Empty transcription")
                return jsonify({
                    "success": False,
                    "error": "Could not transcribe audio. Please speak clearly.",
                    "listen": True
                })
            
            logger.info(f"[STT] Transcribed: '{user_text}'")
            
            try:
                os.remove(tmp_path)
            except:
                pass
        
        except Exception as e:
            logger.error(f"[STT] Transcription error: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Transcription failed: {str(e)}",
                "listen": True
            }), 500
        
        # ===== STEP 3: CHECK INPUT QUALITY =====
        low_confidence = False
        if is_low_quality_input(user_text):
            logger.warning(f"[QUALITY] Low-confidence input: '{user_text}'")
            low_confidence = True
            
            response_text = (
                "मुझे साफ़ सुनाई नहीं दिया।\n"
                "कृपया पूरा वाक्य बोलें।\n\n"
                "उदाहरण:\n"
                "'मुझे सरकारी योजना चाहिए'"
            )
            
            logger.info(f"[RESPONSE] Asking for clarification")
        
        # ===== STEP 4: CHECK EXIT CONDITION =====
        elif any(w in user_text.lower() for w in ['समाप्त', 'exit', 'quit', 'बंद']):
            logger.info("[VOICE] User requested exit")
            
            response_text = "धन्यवाद! आपने हमारी सेवा का उपयोग किया। फिर से मिलेंगे।"
            
            logger.info(f"[RESPONSE] Exit message: {response_text}")
            
            # Generate audio
            audio_file = tts.generate_audio(response_text)
            audio_data = None
            if audio_file:
                # Audio playback will be handled by the browser
                with open(audio_file, 'rb') as f:
                    audio_data = base64.b64encode(f.read()).decode('utf-8')
                try:
                    os.remove(audio_file)
                except:
                    pass
            
            return jsonify({
                "success": True,
                "user_text": user_text,
                "agent_text": response_text,
                "audio": audio_data,
                "listen": False,  # STOP LISTENING
                "low_confidence": False
            })
        
        else:
            # ===== STEP 5: PROCESS THROUGH AGENT =====
            logger.info(f"[PLANNER] Processing user input: '{user_text}'")
            
            try:
                # Get current state or create new
                state_data = conversation_state[session_id]
                
                # Create agent state
                state = AgentState(
                    user_input=user_text,
                    messages=state_data['messages'] + [{'role': 'user', 'content': user_text}],
                    turn_count=state_data['turn_count'] + 1,
                    current_intent='find_schemes'
                )
                
                # Update profile with existing data
                state['age'] = state_data['profile'].get('age')
                state['income'] = state_data['profile'].get('income')
                state['gender'] = state_data['profile'].get('gender')
                state['category'] = state_data['profile'].get('category')
                
                logger.info(f"[AGENT] Current profile: age={state.get('age')}, income={state.get('income')}, gender={state.get('gender')}")
                
                # Run through LangGraph
                logger.info("[AGENT] Running LangGraph workflow...")
                logger.info("[AGENT] ├─ Planner node")
                logger.info("[AGENT] ├─ Executor node")
                logger.info("[AGENT] ├─ Evaluator node")
                logger.info("[AGENT] └─ Response node")
                
                result = agent_graph.invoke(state)
                
                logger.info("[AGENT] ✅ Workflow completed")
                
                # Extract response
                response_text = result.get('messages', [{}])[-1].get('content', 'कोई प्रतिक्रिया नहीं')
                
                logger.info(f"[RESPONSE] Agent: '{response_text[:50]}...'")
                
                # Update conversation state
                state_data['turn_count'] += 1
                state_data['messages'].append({'role': 'user', 'content': user_text})
                state_data['messages'].append({'role': 'assistant', 'content': response_text})
                state_data['profile']['age'] = result.get('age')
                state_data['profile']['income'] = result.get('income')
                state_data['profile']['gender'] = result.get('gender')
                state_data['profile']['category'] = result.get('category')
                
            except Exception as e:
                logger.error(f"[AGENT] Error: {e}", exc_info=True)
                response_text = "क्षमा करें, कोई समस्या आई। कृपया दोबारा प्रयास करें।"
        
        # ===== STEP 6: GENERATE RESPONSE AUDIO (TTS) =====
        try:
            logger.info(f"[TTS] Generating audio for: '{response_text[:40]}...'")
            audio_file = tts.generate_audio(response_text)
            
            audio_data = None
            if audio_file:
                # Audio playback will be handled by the browser
                with open(audio_file, 'rb') as f:
                    audio_data = base64.b64encode(f.read()).decode('utf-8')
                logger.info(f"[TTS] Audio generated: {len(audio_data)} bytes")
                
                try:
                    os.remove(audio_file)
                except:
                    pass
            else:
                logger.warning("[TTS] Failed to generate audio")
        
        except Exception as e:
            logger.error(f"[TTS] TTS error: {e}", exc_info=True)
            audio_data = None
        
        # ===== STEP 7: RETURN RESPONSE =====
        # STRICT RULE: After agent responds, WAIT for next user action
        # Do NOT auto-start recording - user must explicitly click "Start Speaking"
        return jsonify({
            "success": True,
            "user_text": user_text,
            "agent_text": response_text,
            "audio": audio_data,
            "listen": False,  # STOP - Wait for user to explicitly click again
            "low_confidence": low_confidence
        })
    
    except Exception as e:
        logger.error(f"[VOICE] Unexpected error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "listen": True
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "version": "2.0",
        "components": {
            "stt": "✅ AssemblyAI",
            "tts": "✅ Google TTS",
            "agent": "✅ LangGraph",
            "conversation": "✅ Full-loop"
        }
    })


# ==================== FRONTEND ====================

@app.route('/')
def index():
    """Serve browser voice conversation interface"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>🎤 Voice Agent - Hindi Government Schemes</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            text-align: center;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .status-box {
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            min-height: 60px;
            display: flex;
            align-items: center;
        }
        
        .status {
            font-size: 16px;
            color: #333;
            word-wrap: break-word;
        }
        
        .status.recording {
            color: #ff4444;
            font-weight: bold;
            animation: pulse 1s infinite;
        }
        
        .status.agent {
            color: #667eea;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .conversation {
            background: #f9f9f9;
            border: 1px solid #eee;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            max-height: 300px;
            overflow-y: auto;
            min-height: 150px;
        }
        
        .message {
            margin-bottom: 10px;
            padding: 8px;
            border-radius: 5px;
        }
        
        .message.user {
            background: #e3f2fd;
            text-align: left;
            margin-left: 20px;
        }
        
        .message.agent {
            background: #f3e5f5;
            text-align: left;
            margin-right: 20px;
        }
        
        .message-label {
            font-weight: bold;
            font-size: 12px;
            color: #666;
            margin-bottom: 3px;
        }
        
        .message-text {
            color: #333;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        button {
            flex: 1;
            padding: 12px 20px;
            font-size: 14px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            min-width: 150px;
        }
        
        .btn-start {
            background: #4CAF50;
            color: white;
        }
        
        .btn-start:hover:not(:disabled) {
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(76,175,80,0.4);
        }
        
        .btn-stop {
            background: #f44336;
            color: white;
        }
        
        .btn-stop:hover:not(:disabled) {
            background: #da190b;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(244,67,54,0.4);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .info {
            background: #fffde7;
            border: 1px solid #f9f0a7;
            padding: 12px;
            border-radius: 5px;
            font-size: 13px;
            color: #333;
            text-align: center;
        }
        
        .error {
            background: #ffebee;
            border: 1px solid #ffcdd2;
            color: #c62828;
        }
        
        .success {
            background: #e8f5e9;
            border: 1px solid #c8e6c9;
            color: #2e7d32;
        }
        
        .spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 सरकारी योजना सहायक</h1>
        <p class="subtitle">Government Schemes Assistant (Hindi Voice)</p>
        
        <div class="status-box">
            <div class="status" id="status">🔄 Initializing...</div>
        </div>
        
        <div class="conversation" id="conversation"></div>
        
        <div class="controls">
            <button class="btn-start" id="startBtn">🎤 Start Recording</button>
            <button class="btn-stop" id="stopBtn" disabled>⏹️ Stop Recording</button>
        </div>
        
        <div class="info" id="info">
            💡 Page is loading. Please wait...
        </div>
    </div>

    <script>
/* ==================== GLOBAL STATE ==================== */
let audioContext = null;
let mediaStream = null;
let processor = null;

let isRecording = false;
let isSubmitting = false;
let isPlaying = false;

let audioChunks = [];
let sessionId = Date.now().toString();
let autoStopTimer = null;

/* ==================== AUDIO CONTEXT ==================== */
function getAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === "suspended") {
        audioContext.resume();
    }
    return audioContext;
}

/* ==================== UI HELPERS ==================== */
function updateStatus(msg, cls = "") {
    const s = document.getElementById("status");
    s.textContent = msg;
    s.className = "status " + cls;
}

function addMessage(role, text) {
    const c = document.getElementById("conversation");
    const d = document.createElement("div");
    d.className = "message " + role;
    d.innerHTML = `<b>${role === "user" ? "👤 You" : "🤖 Agent"}:</b> ${text}`;
    c.appendChild(d);
    c.scrollTop = c.scrollHeight;
}

/* ==================== START ==================== */
function getGreetingAndStart() {
    updateStatus("🔄 Getting greeting...", "agent");
    document.getElementById("startBtn").disabled = true;
    
    fetch(`/api/start?session_id=${sessionId}`)
        .then(r => r.json())
        .then(data => {
            addMessage("agent", data.text);
            // After greeting, automatically start recording
            if (data.audio) {
                playAgentAudio(data.audio, true);  // Auto-continue to recording
            } else {
                startRecording();
            }
        })
        .catch(e => {
            console.error("Greeting error:", e);
            updateStatus("❌ Connection error", "error");
            document.getElementById("startBtn").disabled = false;
        });
}

/* ==================== RECORDING ==================== */
function startRecording() {
    if (isRecording || isSubmitting || isPlaying) return;

    document.getElementById("startBtn").disabled = true;
    document.getElementById("stopBtn").disabled = false;

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaStream = stream;
        const ctx = getAudioContext();

        const source = ctx.createMediaStreamSource(stream);
        processor = ctx.createScriptProcessor(4096, 1, 1);

        audioChunks = [];
        isRecording = true;

        source.connect(processor);
        processor.connect(ctx.destination);

        processor.onaudioprocess = e => {
            if (!isRecording) return;
            const input = e.inputBuffer.getChannelData(0);
            const pcm = new Int16Array(input.length);
            for (let i = 0; i < input.length; i++) {
                pcm[i] = Math.max(-1, Math.min(1, input[i])) * 0x7fff;
            }
            audioChunks.push(pcm);
        };

        updateStatus("🎤 Recording...", "recording");

        autoStopTimer = setTimeout(stopRecording, 8000);
    }).catch(e => {
        console.error("Mic error:", e);
        isRecording = false;
        document.getElementById("startBtn").disabled = false;
        document.getElementById("stopBtn").disabled = true;
        updateStatus("❌ Microphone access denied", "error");
    });
}

/* ==================== STOP RECORDING (SAFE) ==================== */
function stopRecording() {
    // Only stop if we're actually recording
    if (!isRecording) return;

    isRecording = false;  // Stop immediately
    document.getElementById("startBtn").disabled = false;
    document.getElementById("stopBtn").disabled = true;

    if (autoStopTimer) clearTimeout(autoStopTimer);
    if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
    if (processor) processor.disconnect();

    // If no audio, just reset and return
    if (audioChunks.length === 0) {
        updateStatus("❌ No audio captured", "error");
        return;
    }

    // Submit once and only once
    submitAudio();
}

/* ==================== SUBMIT AUDIO ==================== */
function submitAudio() {
    // Lock to prevent duplicate submissions
    if (isSubmitting) return;
    isSubmitting = true;

    updateStatus("📤 Sending audio...", "agent");

    const wav = encodeWAV(audioChunks, 16000);
    const b64 = btoa(String.fromCharCode(...new Uint8Array(wav)));

    fetch("/api/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: b64, session_id: sessionId })
    })
    .then(r => r.json())
    .then(data => {
        // Add messages to conversation
        if (data.user_text) addMessage("user", data.user_text);
        if (data.agent_text) addMessage("agent", data.agent_text);

        // STRICT RULE: Check if server wants to continue listening
        const shouldContinueListening = data.listen === true;

        // Play agent response
        if (data.audio) {
            playAgentAudio(data.audio, shouldContinueListening);
        } else {
            // No audio response - check if we should continue
            isSubmitting = false;
            if (shouldContinueListening) {
                // Auto-continue conversation (rare case)
                setTimeout(() => startRecording(), 500);
            } else {
                // WAIT - User must explicitly click "Start Speaking" again
                updateStatus("✅ Ready - Click 'Start Speaking' to continue", "agent");
            }
        }
    })
    .catch(e => {
        console.error("Submit error:", e);
        isSubmitting = false;
        updateStatus("❌ Network error", "error");
    });
}

/* ==================== PLAY AGENT AUDIO ==================== */
function playAgentAudio(base64Audio, shouldContinueListening = false) {
    if (isPlaying) return;
    isPlaying = true;

    const ctx = getAudioContext();
    const bytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));

    ctx.decodeAudioData(bytes.buffer, buffer => {
        const src = ctx.createBufferSource();
        src.buffer = buffer;
        src.connect(ctx.destination);

        updateStatus("📢 Agent speaking...", "agent");

        // When audio finishes, check if we should continue listening
        src.onended = () => {
            isPlaying = false;
            isSubmitting = false;

            // STRICT RULE: Only auto-continue if server explicitly says to OR initial greeting
            if (shouldContinueListening) {
                // After greeting or when server says continue, start recording
                setTimeout(() => startRecording(), 500);
            } else {
                // Wait for explicit user action
                updateStatus("✅ Ready - Click 'Start Recording' to continue", "agent");
                document.getElementById("startBtn").disabled = false;
            }
        };

        src.start();
    }, err => {
        console.error("Decode error:", err);
        isPlaying = false;
        isSubmitting = false;
        updateStatus("❌ Audio playback error", "error");
        document.getElementById("startBtn").disabled = false;
    });
}

/* ==================== WAV ENCODER ==================== */
function encodeWAV(chunks, rate) {
    let length = chunks.reduce((s, c) => s + c.length, 0);
    let pcm = new Int16Array(length);
    let offset = 0;
    chunks.forEach(c => { pcm.set(c, offset); offset += c.length; });

    const buffer = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(buffer);

    const write = (o, s) => [...s].forEach((c, i) => view.setUint8(o + i, c.charCodeAt(0)));

    write(0, "RIFF");
    view.setUint32(4, 36 + pcm.length * 2, true);
    write(8, "WAVEfmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, rate, true);
    view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    write(36, "data");
    view.setUint32(40, pcm.length * 2, true);

    new Uint8Array(buffer, 44).set(new Uint8Array(pcm.buffer));
    return buffer;
}

// Initialize
window.addEventListener("load", () => {
    updateStatus("✅ Click 'Start Recording' to begin", "agent");
    document.getElementById("info").innerHTML = "💡 <b>Say your name or tell us what government schemes you need help with.</b>";
    document.getElementById("startBtn").disabled = false;
    
    // Set up button event listeners
    document.getElementById("startBtn").addEventListener("click", getGreetingAndStart);
    document.getElementById("stopBtn").addEventListener("click", stopRecording);
});
    </script>
</body>
</html>
    """
    return render_template_string(html)


def main():
    """Start web server"""
    logger.info("=" * 70)
    logger.info("🌐 Browser Voice Agent Web Server v2.0")
    logger.info("=" * 70)
    logger.info("📱 OPEN IN BROWSER:")
    logger.info("   http://127.0.0.1:5000")
    logger.info("")
    logger.info("🎤 Features:")
    logger.info("   ✓ Full voice conversation loop")
    logger.info("   ✓ Automatic STT/TTS")
    logger.info("   ✓ Hindi language support")
    logger.info("   ✓ Low-confidence detection")
    logger.info("   ✓ Conversation memory")
    logger.info("=" * 70)
    
    try:
        app.run(debug=False, host='127.0.0.1', port=5001, threaded=True, use_reloader=False)
    except OSError:
        logger.warning("Port 5001 in use, trying 5002...")
        app.run(debug=False, host='127.0.0.1', port=5002, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()

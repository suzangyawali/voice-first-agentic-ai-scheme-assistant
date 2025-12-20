"""
Main Application
Voice-First LangGraph Agent for Government Schemes (Hindi)
"""

import asyncio
import logging
from pathlib import Path
import argparse

from graph import create_agent_graph
from voice.stt import HindiSTT
from voice.tts import HindiTTS

# Create necessary directories BEFORE logging setup
Path('logs').mkdir(exist_ok=True)
Path('audio_files').mkdir(exist_ok=True)
Path('transcripts').mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def is_low_confidence(text: str) -> bool:
    """
    Detect if transcribed speech has low confidence.
    """
    text = text.strip()

    if len(text) < 6:
        logger.warning(f"[LOW_CONFIDENCE_ASR] Text too short: '{text}'")
        return True

    segments = text.split()
    if len(segments) < 2:
        alpha_count = sum(1 for c in text if c.isalpha())
        alpha_ratio = alpha_count / len(text)
        if alpha_ratio < 0.45:
            logger.warning(f"[LOW_CONFIDENCE_ASR] Gibberish pattern: '{text}'")
            return True

    return False


class VoiceAgentApp:
    """
    Main Voice Agent Application
    Integrates LangGraph workflow with voice interface
    """

    def __init__(self, language: str = 'hindi', mode: str = 'demo'):
        self.language = language
        self.mode = mode

        logger.info("Initializing Voice Agent Application...")

        self.agent = create_agent_graph('data/schemes_hindi.json')

        self.stt = HindiSTT(debug_audio=True)
        self.tts = HindiTTS()

        self.thread_id = "session_001"
        self.turn_count = 0

        logger.info(f"Application initialized: {language}, mode: {mode}")
        logger.info("\n" + self.agent.get_graph_visualization())

    async def start(self):
        logger.info("=" * 60)
        logger.info("🎙️ Voice-First LangGraph Agent Started")
        logger.info(f"Language: Hindi (हिन्दी)")
        logger.info(f"Mode: {self.mode}")
        logger.info("=" * 60)

        if self.mode == 'interactive':
            await self._interactive_mode()
        elif self.mode == 'demo':
            await self._demo_mode()
        elif self.mode == 'test':
            await self._test_mode()
        elif self.mode == 'type':
            await self._type_mode()

    async def _interactive_mode(self):
        welcome = "नमस्ते! मैं आपकी सरकारी योजनाओं में मदद के लिए यहाँ हूँ।"
        await self.tts.speak(welcome)

        print("\n🎤 Voice Agent Ready! Say 'समाप्त करें' to end.\n")

        while True:
            try:
                user_input = await self.stt.listen(max_duration=10.0)

                if not user_input:
                    await self.tts.speak("मुझे साफ सुनाई नहीं दिया।")
                    continue

                if is_low_confidence(user_input):
                    await self.tts.speak(
                        "माफ़ कीजिए, आपकी आवाज़ स्पष्ट नहीं थी। कृपया फिर से बोलें।"
                    )
                    continue

                if any(w in user_input.lower() for w in ['समाप्त', 'exit', 'quit', 'बंद']):
                    await self.tts.speak("धन्यवाद! आपका दिन शुभ हो!")
                    break

                await self._process_turn(user_input)

            except KeyboardInterrupt:
                await self.tts.speak("धन्यवाद!")
                break
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                await self.tts.speak("क्षमा करें, कोई समस्या आई।")

    # ====================== TYPE MODE (ONLY ADDITION) ======================

    async def _type_mode(self):
        """
        TYPE MODE
        User types → agent speaks typed text → agent answers
        """

        intro = (
            "टाइप मोड शुरू हो गया है। "
            "आप हिंदी में टाइप करें। "
            "मैं पहले आपके टाइप किए गए शब्द बोलूँगा, "
            "फिर उत्तर दूँगा।"
        )
        await self.tts.speak(intro)

        print("\n⌨️ TYPE MODE")
        print("NOTE: Typed input is treated as simulated speech.")
        print("बाहर निकलने के लिए 'exit' लिखें\n")

        while True:
            try:
                user_input = input("आप: ").strip()

                if not user_input:
                    print("⚠️ कृपया कुछ लिखें।")
                    continue

                if user_input.lower() in ['exit', 'quit', 'समाप्त', 'बंद']:
                    await self.tts.speak("धन्यवाद! आपका दिन शुभ हो!")
                    break

                # 📝 LOG recovery / simulation
                logger.info("[RECOVERY_MODE] Using typed input as simulated speech")

                # 🔊 Speak what user typed
                await self.tts.speak(f"आपने टाइप किया: {user_input}")

                # 🔁 Normal agent pipeline (UNCHANGED)
                await self._process_turn(user_input)

            except KeyboardInterrupt:
                await self.tts.speak("धन्यवाद!")
                break
            except Exception as e:
                logger.error(f"Type mode error: {e}", exc_info=True)
                await self.tts.speak("क्षमा करें, कोई समस्या आई।")

    # ====================== DEMO MODE (UNCHANGED) ======================

    async def _demo_mode(self):
        scenarios = [
            {
                'name': 'सफल प्रवाह - छात्रवृत्ति खोज',
                'inputs': [
                    'मुझे सरकारी योजना चाहिए',
                    'मेरी उम्र 20 साल है',
                    'मेरी आय 2 लाख रुपये है',
                    'मैं पुरुष हूं'
                ]
            }
        ]

        for scenario in scenarios:
            self.agent.reset_conversation(self.thread_id)
            self.turn_count = 0

            for text in scenario['inputs']:
                await self._process_turn(text, is_demo=True)
                await asyncio.sleep(1.5)

        print("\n✅ Demo completed")

    async def _test_mode(self):
        tests = [
            'मुझे सरकारी योजना चाहिए',
            'मेरी उम्र 25 साल है',
            'मेरी आय 2 लाख रुपये है',
            'मैं पुरुष हूं'
        ]

        for t in tests:
            result = await self.agent.process_input(t, self.thread_id)
            print("Input:", t)
            print("Response:", result['response'][:60], "\n")

    async def _process_turn(self, user_input: str, is_demo: bool = False):
        self.turn_count += 1

        logger.info("=" * 60)
        logger.info(f"TURN {self.turn_count}")
        logger.info(f"User: {user_input}")

        result = await self.agent.process_input(user_input, self.thread_id)

        response = result['response']
        metadata = result['metadata']

        logger.info(f"Agent: {response}")
        logger.info(f"Intent: {metadata.get('intent')}")
        logger.info(f"Extracted: {metadata.get('extracted_info')}")
        logger.info(f"Eligible Schemes: {metadata.get('eligible_schemes')}")

        print(f"\n🤖 Agent: {response}\n")

        if self.mode != 'test':
            if not is_demo:
                await self.tts.speak(response)
            else:
                await asyncio.sleep(len(response) * 0.04)


async def main():
    parser = argparse.ArgumentParser(
        description='Voice-First LangGraph Agent (Hindi)'
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='demo',
        choices=['interactive', 'demo', 'test', 'type'],
        help='Operation mode'
    )
    parser.add_argument(
        '--language',
        type=str,
        default='hindi',
        help='Language (hindi)'
    )

    args = parser.parse_args()

    app = VoiceAgentApp(language=args.language, mode=args.mode)

    try:
        await app.start()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        logger.info("Application terminated")


if __name__ == '__main__':
    asyncio.run(main())

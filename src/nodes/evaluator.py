"""
Evaluator and Response Nodes
Deterministic decision + response generation (FINAL FIXED)
"""

import logging
from typing import Literal
from state.schema import AgentState
from llm.config import get_llm_manager

logger = logging.getLogger(__name__)

FIELD_LABELS_HI = {
    "age": "उम्र",
    "income": "आय",
    "gender": "लिंग",
}


# ===================== EVALUATOR ===================== #

class EvaluatorNode:
    """
    Evaluator Node
    - Checks profile completeness
    - Stops looping after application
    """

    def __init__(self):
        logger.info("Evaluator node initialized")

    def __call__(self, state: AgentState) -> AgentState:
        logger.info("[EVALUATOR] Evaluating execution results")

        # ✅ Application finished OR error occurred → respond directly
        if state.get("application_result") or state.get("error"):
            state["next_step"] = "respond"
            return state

        required = ["age", "income", "gender"]
        missing = [f for f in required if not state.get(f)]

        if missing:
            state["missing_information"] = missing

        state["next_step"] = "respond"
        return state


# ===================== RESPONSE ===================== #

class ResponseNode:
    """
    Response Node
    - Deterministic
    - Error-first handling
    - No duplicate-apply loop
    """

    def __init__(self):
        self.llm_manager = get_llm_manager()
        logger.info("Response node initialized")

    def __call__(self, state: AgentState) -> AgentState:
        logger.info("[RESPONSE] Generating response")

        response = self._generate_response(state)

        state["messages"].append(
            {"role": "assistant", "content": response}
        )

        state["turn_count"] += 1
        state["should_continue"] = False
        return state

    # ===================== RESPONSE LOGIC ===================== #

    def _generate_response(self, state: AgentState) -> str:

        # 🚫 DUPLICATE APPLICATION (TOP PRIORITY FIX)
        if state.get("error") == "already_applied":
            return (
                "आप इस योजना के लिए पहले ही आवेदन कर चुके हैं। ✅\n\n"
                "क्या आप किसी अन्य योजना की जानकारी चाहते हैं?"
            )

        # 🚫 NO SCHEME SELECTED
        if state.get("error") == "no_scheme_selected":
            return (
                "कृपया पहले किसी योजना का चयन करें, "
                "फिर मैं आपका आवेदन कर सकूँगा।"
            )

        # 1️⃣ APPLICATION SUCCESS
        if state.get("application_result"):
            app = state["application_result"]
            return (
                "आपका आवेदन सफलतापूर्वक जमा हो गया है ✅\n\n"
                f"आवेदन आईडी: {app.get('application_id')}\n"
                f"स्थिति: {app.get('status')}\n"
                f"अनुमानित प्रक्रिया समय: {app.get('estimated_processing_days')} दिन\n\n"
                "क्या आप किसी अन्य योजना की जानकारी चाहते हैं?"
            )

        # 2️⃣ ELIGIBLE SCHEMES
        if state.get("eligible_schemes"):
            return self._present_schemes(state)

        # 3️⃣ MISSING INFO
        if state.get("missing_information"):
            fields_hi = [
                FIELD_LABELS_HI.get(f, f)
                for f in state["missing_information"]
            ]
            return "कृपया निम्न जानकारी प्रदान करें: " + ", ".join(fields_hi)

        # 4️⃣ FALLBACK
        return "कृपया अपनी जानकारी साझा करें ताकि मैं आपकी सहायता कर सकूँ।"

    def _present_schemes(self, state: AgentState) -> str:
        schemes = state.get("eligible_schemes", [])

        response = f"आप निम्नलिखित {len(schemes)} सरकारी योजना के लिए पात्र हैं:\n\n"

        for i, s in enumerate(schemes[:5], 1):
            response += (
                f"{i}. {s.get('name_hindi', s.get('name'))}\n"
                f"   विवरण: {s.get('description_hindi', '')}\n"
                f"   लाभ: {s.get('benefits', 'उपलब्ध')}\n\n"
            )

        response += "क्या आप किसी योजना के लिए आवेदन करना चाहते हैं?"
        return response


# ===================== ROUTERS ===================== #

def should_continue(state: AgentState) -> Literal["continue", "end"]:
    return "end"


def route_after_planner(state: AgentState) -> Literal["executor", "respond", "evaluator"]:
    return state.get("next_step", "respond")


def route_after_evaluator(state: AgentState) -> Literal["respond"]:
    return "respond"


# ===================== SINGLETONS ===================== #

evaluator_node = EvaluatorNode()
response_node = ResponseNode()

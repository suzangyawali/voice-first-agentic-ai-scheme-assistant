"""
Evaluator and Response Nodes
Deterministic decision + response generation
"""

import logging
from typing import Literal
from state.schema import AgentState
from llm.config import get_llm_manager

logger = logging.getLogger(__name__)


# 🔑 Internal → Hindi mapping (CRITICAL FIX)
FIELD_LABELS_HI = {
    "age": "उम्र",
    "income": "आय",
    "gender": "लिंग",
}


class EvaluatorNode:
    """
    Evaluator Node
    - Checks profile completeness
    - Never invents facts
    """

    def __init__(self):
        logger.info("Evaluator node initialized")

    def __call__(self, state: AgentState) -> AgentState:
        logger.info("[EVALUATOR] Evaluating execution results")

        required = ["age", "income", "gender"]
        missing = [f for f in required if not state.get(f)]

        logger.info(f"[EVALUATOR] Missing fields: {missing}")

        if missing:
            state["missing_information"] = missing
            state["next_step"] = "respond"
            return state

        # Profile complete
        state["next_step"] = "respond"
        return state


class ResponseNode:
    """
    Response Node
    - Deterministic
    - NO hallucination
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

        logger.info(f"[RESPONSE] Generated: {response[:80]}")
        return state

    # ---------------- RESPONSE LOGIC ---------------- #

    def _generate_response(self, state: AgentState) -> str:
        # 1️⃣ Eligible schemes → deterministic
        if state.get("eligible_schemes"):
            return self._present_schemes(state)

        # 2️⃣ Missing info → ask in HINDI (✅ FIX)
        if state.get("missing_information"):
            fields_hi = [
                FIELD_LABELS_HI.get(f, f)
                for f in state["missing_information"]
            ]
            return (
                "कृपया निम्न जानकारी प्रदान करें: "
                + ", ".join(fields_hi)
            )

        # 3️⃣ Fallback
        return "कृपया अपनी जानकारी साझा करें ताकि मैं आपकी सहायता कर सकूँ।"

    def _present_schemes(self, state: AgentState) -> str:
        schemes = state.get("eligible_schemes", [])

        response = f"आप निम्नलिखित {len(schemes)} सरकारी योजना के लिए पात्र हैं:\n\n"

        for i, s in enumerate(schemes[:5], 1):
            response += (
                f"{i}. {s.get('name_hindi', s.get('name'))}\n"
                f"   विवरण: {s.get('description_hindi', s.get('description', ''))}\n"
                f"   लाभ: {s.get('benefits', 'उपलब्ध')}\n\n"
            )

        response += "क्या आप किसी योजना के लिए आवेदन करना चाहते हैं?"
        return response


# ---------------- ROUTER ---------------- #

def should_continue(state: AgentState) -> Literal["continue", "end"]:
    logger.info("[ROUTER] Response complete - ending workflow")
    return "end"


def route_after_planner(state: AgentState) -> Literal["executor", "respond", "evaluator"]:
    return state.get("next_step", "respond")


def route_after_evaluator(state: AgentState) -> Literal["respond"]:
    return "respond"


# Singletons
evaluator_node = EvaluatorNode()
response_node = ResponseNode()

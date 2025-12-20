"""
Planner Node
Analyzes user input and decides next action in LangGraph workflow
Uses LLM for intent classification
"""

import logging
from state.schema import AgentState
from llm.config import get_llm_manager
from llm.prompts import get_prompt

logger = logging.getLogger(__name__)


class PlannerNode:
    """
    Planner Node in LangGraph workflow
    Responsibilities:
    - Identify user intent using LLM
    - Decide routing (executor / respond)
    """

    def __init__(self):
        self.llm_manager = get_llm_manager()

        self.valid_intents = [
            "find_schemes",
            "provide_info",
            "apply_scheme",
            "get_details",
            "clarify",
            "greeting",
        ]

        logger.info("Planner node initialized with LLM-based intent classification")

    def __call__(self, state: AgentState) -> AgentState:
        logger.info(f"[PLANNER] Processing turn {state['turn_count']}")
        logger.info(f"[PLANNER] User input: {state['user_input'][:60]}")

        intent = self._identify_intent(state)
        state["current_intent"] = intent

        logger.info(f"[PLANNER] Identified intent: {intent}")

        # Greeting → respond directly
        if intent == "greeting":
            state["next_step"] = "respond"
            return state

        # 🔒 CRITICAL RULE:
        # Planner NEVER routes to evaluator
        # Executor ALWAYS runs next
        state["next_step"] = "executor"
        return state

    # ----------------- INTERNALS ----------------- #

    def _identify_intent(self, state: AgentState) -> str:
        prompt = get_prompt(
            "intent_classification",
            user_input=state["user_input"]
        )
        response = self.llm_manager.invoke(prompt)

        result = self.llm_manager.parse_json_response(response) or {}

        intent = result.get("intent", "find_schemes")
        confidence = result.get("confidence", 0.5)

        logger.info(f"[PLANNER] LLM Intent: {intent} (confidence: {confidence})")

        if intent not in self.valid_intents:
            logger.warning(f"[PLANNER] Invalid intent '{intent}', defaulting")
            intent = "find_schemes"

        state["intent_confidence"] = confidence
        return intent


# Singleton
planner_node = PlannerNode()

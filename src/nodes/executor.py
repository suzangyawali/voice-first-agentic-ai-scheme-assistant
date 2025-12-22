import logging
import re
from typing import Dict, Any, Optional

from state.schema import AgentState, update_profile
from llm.config import get_llm_manager
from llm.prompts import get_prompt

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.6


# ===================== NORMALIZATION ===================== #

def normalize_gender(value: str) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    if v in ["पुरुष", "male", "m"]:
        return "male"
    if v in ["महिला", "female", "f"]:
        return "female"
    return None


def normalize_category(value: str) -> Optional[str]:
    if not value:
        return None
    v = value.upper()
    if "एससी" in v or v == "SC":
        return "SC"
    if "एसटी" in v or v == "ST":
        return "ST"
    if "ओबीसी" in v or v == "OBC":
        return "OBC"
    if "GENERAL" in v or "सामान्य" in v:
        return "GENERAL"
    return None


# ===================== INPUT QUALITY ===================== #

def is_low_quality_input(text: str) -> bool:
    t = text.strip()
    if len(t) < 6:
        return True
    words = t.split()
    if len(words) == 1:
        return True
    noise_words = ["हां", "हुँ", "अच्छा", "नमस्ते"]
    if len(words) <= 2 and any(w in noise_words for w in words):
        return True
    return False


# ===================== EXECUTOR NODE ===================== #

class ExecutorNode:
    """
    Executor Node
    - State-aware
    - Memory-safe
    - Duplicate-application protected
    """

    def __init__(self, eligibility_tool, application_tool):
        self.eligibility_tool = eligibility_tool
        self.application_tool = application_tool
        self.llm_manager = get_llm_manager()

        self.extractors = {
            "age": self._extract_age_regex,
            "income": self._extract_income_regex,
            "gender": self._extract_gender_regex,
            "category": self._extract_category_regex,
            "occupation": self._extract_occupation_regex,
        }

        logger.info("Executor node initialized")

    # ===================== MAIN ===================== #

    def __call__(self, state: AgentState) -> AgentState:
        logger.info("[EXECUTOR] Executing")

        # ✅ Ensure memory exists
        state.setdefault("applied_schemes", [])

        user_text = state["user_input"]

        if is_low_quality_input(user_text):
            state["needs_clarification"] = True
            state["next_step"] = "evaluator"
            return state

        # 🔍 Extract info
        extracted = self._extract_all_info(user_text)
        for field, value in extracted.items():
            state = update_profile(state, field, value)

        intent = state.get("current_intent")

        # 🔎 Eligibility check
        if intent in ["find_schemes", "provide_info"]:
            if state.get("age") and state.get("income") and state.get("gender"):
                state = self._execute_eligibility_check(state)

        # 📝 Application
        elif intent == "apply_scheme":
            state = self._execute_application(state)

        state["next_step"] = "evaluator"
        return state

    # ===================== EXTRACTION ===================== #

    def _extract_all_info(self, text: str) -> Dict[str, Any]:
        prompt = get_prompt("information_extraction", user_input=text)
        response = self.llm_manager.invoke(prompt)

        result = self.llm_manager.parse_json_response(response)
        if not result or float(result.get("confidence", 0)) < CONFIDENCE_THRESHOLD:
            return self._regex_only(text)

        extracted = {}

        if "age" in result.get("extracted_fields", []):
            extracted["age"] = result.get("age")

        if "annual_income" in result.get("extracted_fields", []):
            extracted["income"] = result.get("annual_income")

        if "gender" in result.get("extracted_fields", []):
            extracted["gender"] = normalize_gender(result.get("gender"))

        if "category" in result.get("extracted_fields", []):
            extracted["category"] = normalize_category(result.get("category"))

        if "occupation" in result.get("extracted_fields", []):
            extracted["occupation"] = result.get("occupation")

        return {k: v for k, v in extracted.items() if v is not None}

    # ===================== REGEX FALLBACK ===================== #

    def _regex_only(self, text: str) -> Dict[str, Any]:
        extracted = {}
        for field, extractor in self.extractors.items():
            val = extractor(text)
            if val is not None:
                extracted[field] = val
        return extracted

    def _extract_age_regex(self, text: str) -> Optional[int]:
        m = re.search(r"(\d+)\s*साल", text)
        return int(m.group(1)) if m else None

    def _extract_income_regex(self, text: str) -> Optional[float]:
        m = re.search(r"(\d+)\s*लाख", text)
        return float(m.group(1)) * 100000 if m else None

    def _extract_gender_regex(self, text: str) -> Optional[str]:
        if "पुरुष" in text:
            return "male"
        if "महिला" in text:
            return "female"
        return None

    def _extract_category_regex(self, text: str) -> Optional[str]:
        return normalize_category(text)

    def _extract_occupation_regex(self, text: str) -> Optional[str]:
        if "किसान" in text:
            return "farmer"
        return None

    # ===================== TOOLS ===================== #

    def _execute_eligibility_check(self, state: AgentState) -> AgentState:
        result = self.eligibility_tool.execute(
            user_profile={
                "age": state.get("age"),
                "income": state.get("income"),
                "gender": state.get("gender"),
                "occupation": state.get("occupation"),
                "category": state.get("category"),
                "applied_schemes": state.get("applied_schemes", []),
            }
        )
        state["eligible_schemes"] = result.get("eligible_schemes", [])
        return state

    def _execute_application(self, state: AgentState) -> AgentState:
        # 🔒 Resolve scheme ONLY ONCE
        scheme_id = state.get("selected_scheme_id")

        if not scheme_id:
            eligible = state.get("eligible_schemes", [])
            if eligible:
                scheme_id = eligible[0]["id"]
                state["selected_scheme_id"] = scheme_id  # 🔐 LOCK

        if not scheme_id:
            state["error"] = "no_scheme_selected"
            return state

        # 🚫 DUPLICATE BLOCK (FIXED)
        if scheme_id in state.get("applied_schemes", []):
            state["error"] = "already_applied"
            return state

        # ▶️ Call application tool
        result = self.application_tool.execute(
            scheme_id=scheme_id,
            user_profile={
                "age": state.get("age"),
                "income": state.get("income"),
                "gender": state.get("gender"),
                "occupation": state.get("occupation"),
                "category": state.get("category"),
            },
        )

        # 🚫 Tool error
        if result.get("error"):
            state["error"] = result["error"]
            state["error_message"] = result.get("message")
            return state

        # ✅ Success
        state["application_result"] = result
        state["applied_schemes"].append(scheme_id)

        return state


def create_executor_node(eligibility_tool, application_tool):
    return ExecutorNode(eligibility_tool, application_tool)

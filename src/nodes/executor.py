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
    Executor Node (STRICT + SAFE MODE)

    Guarantees:
    - Accepts ONLY explicitly mentioned user info
    - NEVER hallucinates
    - Regex fallback when LLM JSON fails
    - Stable for Hindi voice input
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

        user_text = state["user_input"]

        # 🚫 Reject meaningless utterances
        if is_low_quality_input(user_text):
            logger.warning("[EXECUTOR] Low-quality input → clarification")
            state["needs_clarification"] = True
            state["next_step"] = "evaluator"
            return state

        extracted = self._extract_all_info(user_text)

        if not extracted:
            logger.info("[EXECUTOR] No explicit info extracted")
            state["needs_clarification"] = True
            state["next_step"] = "evaluator"
            return state

        logger.info(f"[EXECUTOR] Accepted explicit fields: {extracted}")
        state["extracted_info"] = extracted

        # ✅ Update profile safely
        for field, value in extracted.items():
            state = update_profile(state, field, value)

        intent = state.get("current_intent")

        # Tool usage
        if intent in ["find_schemes", "provide_info"]:
            if state.get("age") and state.get("income") and state.get("gender"):
                state = self._execute_eligibility_check(state)
            else:
                logger.info("[EXECUTOR] Profile incomplete → skip eligibility")

        elif intent == "apply_scheme":
            state = self._execute_application(state)

        state["next_step"] = "evaluator"
        return state

    # ===================== EXTRACTION ===================== #

    def _extract_all_info(self, text: str) -> Dict[str, Any]:
        prompt = get_prompt("information_extraction", user_input=text)
        response = self.llm_manager.invoke(prompt)

        logger.info(f"[EXECUTOR] LLM raw response: {response[:150]}...")

        # 🚑 HARD FAIL → REGEX
        result = self.llm_manager.parse_json_response(response)
        if not result:
            logger.warning("[EXECUTOR] JSON parse failed → regex fallback")
            return self._regex_only(text)

        confidence = float(result.get("confidence", 0.0))
        explicit_fields = set(result.get("extracted_fields", []))

        # 🔴 LOW CONFIDENCE → REGEX ONLY
        if confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"[EXECUTOR] Low confidence ({confidence}) → regex only")
            return self._regex_only(text)

        extracted: Dict[str, Any] = {}

        if "age" in explicit_fields and isinstance(result.get("age"), int):
            extracted["age"] = result["age"]

        if "annual_income" in explicit_fields and result.get("annual_income") is not None:
            extracted["income"] = float(result["annual_income"])

        if "gender" in explicit_fields and result.get("gender"):
            g = normalize_gender(result["gender"])
            if g:
                extracted["gender"] = g

        if "category" in explicit_fields and result.get("category"):
            c = normalize_category(result["category"])
            if c:
                extracted["category"] = c

        if "occupation" in explicit_fields and result.get("occupation"):
            extracted["occupation"] = result["occupation"]

        return extracted

    # ===================== REGEX (FALLBACK) ===================== #

    def _regex_only(self, text: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        for field, extractor in self.extractors.items():
            val = extractor(text)
            if val is not None:
                extracted[field] = val
        return extracted

    def _extract_age_regex(self, text: str) -> Optional[int]:
        text = self._convert_hindi_numerals(text)
        m = re.search(r"(?:उम्र|आयु)\s*(\d+)|(\d+)\s*साल", text)
        if m:
            age = int(m.group(1) or m.group(2))
            if 1 <= age <= 120:
                return age
        return None

    def _extract_income_regex(self, text: str) -> Optional[float]:
        text = self._convert_hindi_numerals(text.lower())
        m = re.search(r"(\d+)\s*लाख", text)
        if m:
            return float(m.group(1)) * 100000
        m = re.search(r"(\d+)\s*हजार", text)
        if m:
            return float(m.group(1)) * 1000
        return None

    def _extract_gender_regex(self, text: str) -> Optional[str]:
        t = text.lower()
        if "पुरुष" in t:
            return "male"
        if "महिला" in t:
            return "female"
        return None

    def _extract_category_regex(self, text: str) -> Optional[str]:
        return normalize_category(text)

    def _extract_occupation_regex(self, text: str) -> Optional[str]:
        mapping = {
            "किसान": "farmer",
            "नौकरी": "employee",
            "छात्र": "student",
            "व्यापारी": "business",
        }
        for k, v in mapping.items():
            if k in text:
                return v
        return None

    def _convert_hindi_numerals(self, text: str) -> str:
        return text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))

    # ===================== TOOLS ===================== #

    def _execute_eligibility_check(self, state: AgentState) -> AgentState:
        try:
            result = self.eligibility_tool.execute(
                user_profile={
                    "age": state.get("age"),
                    "income": state.get("income"),
                    "gender": state.get("gender"),
                    "occupation": state.get("occupation"),
                    "category": state.get("category"),
                }
            )
            state["eligible_schemes"] = result.get("eligible_schemes", [])
        except Exception as e:
            state["error"] = f"eligibility_error: {str(e)}"
        return state

    def _execute_application(self, state: AgentState) -> AgentState:
        try:
            scheme_id = state.get("selected_scheme_id")
            if not scheme_id and state.get("eligible_schemes"):
                scheme_id = state["eligible_schemes"][0]["id"]

            if not scheme_id:
                state["error"] = "no_scheme_selected"
                return state

            state["application_result"] = self.application_tool.execute(
                scheme_id=scheme_id,
                user_profile={
                    "age": state.get("age"),
                    "income": state.get("income"),
                    "gender": state.get("gender"),
                    "occupation": state.get("occupation"),
                    "category": state.get("category"),
                },
            )
            state["selected_scheme_id"] = scheme_id
        except Exception as e:
            state["error"] = f"application_error: {str(e)}"
        return state


def create_executor_node(eligibility_tool, application_tool):
    return ExecutorNode(eligibility_tool, application_tool)

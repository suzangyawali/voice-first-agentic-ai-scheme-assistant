"""
Agent State Schema
Defines the state structure for LangGraph workflow
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime
import operator


class AgentState(TypedDict):
    """
    State schema for the government scheme assistant agent
    This state flows through all LangGraph nodes
    """

    # ======================
    # User Input
    # ======================
    messages: Annotated[List[Dict[str, str]], operator.add]
    user_input: str

    # ======================
    # User Profile
    # ======================
    age: Optional[int]
    income: Optional[float]
    gender: Optional[str]
    occupation: Optional[str]
    category: Optional[str]
    state_location: Optional[str]
    has_disabilities: Optional[bool]
    is_student: Optional[bool]
    marital_status: Optional[str]

    # ======================
    # Agent Processing
    # ======================
    current_intent: Optional[str]
    missing_information: List[str]

    # ======================
    # Tool Results
    # ======================
    eligible_schemes: List[Dict[str, Any]]
    selected_scheme_id: Optional[str]
    application_result: Optional[Dict[str, Any]]

    # ======================
    # Memory & Context
    # ======================
    contradictions: Annotated[List[Dict[str, Any]], operator.add]
    extracted_info: Dict[str, Any]

    # ✅ CRITICAL FIX (PERSISTENT MEMORY)
    applied_schemes: List[str]

    # ======================
    # Control Flow
    # ======================
    next_step: Optional[str]
    should_continue: bool
    error: Optional[str]

    # ======================
    # Metadata
    # ======================
    turn_count: int
    confidence: float


def create_initial_state() -> AgentState:
    """Create initial agent state"""
    return AgentState(
        messages=[],
        user_input="",

        age=None,
        income=None,
        gender=None,
        occupation=None,
        category=None,
        state_location=None,
        has_disabilities=None,
        is_student=None,
        marital_status=None,

        current_intent=None,
        missing_information=[],
        eligible_schemes=[],
        selected_scheme_id=None,
        application_result=None,

        contradictions=[],
        extracted_info={},

        # ✅ INITIALIZED MEMORY
        applied_schemes=[],

        next_step="planner",
        should_continue=True,
        error=None,
        turn_count=0,
        confidence=1.0
    )


def update_profile(state: AgentState, field: str, value: Any) -> AgentState:
    """
    Update user profile field and detect contradictions
    """
    old_value = state.get(field)

    if old_value is not None and old_value != value:
        contradiction = {
            "field": field,
            "old_value": old_value,
            "new_value": value,
            "timestamp": datetime.now().isoformat(),
        }
        state["contradictions"].append(contradiction)

    state[field] = value
    state["extracted_info"][field] = value
    return state


def get_missing_info(state: AgentState, required_fields: List[str]) -> List[str]:
    """Return list of missing required fields"""
    return [f for f in required_fields if state.get(f) is None]


def is_profile_complete(state: AgentState, intent: str = "find_schemes") -> bool:
    required_fields = {
        "find_schemes": ["age", "income", "gender"],
        "apply_scheme": ["age", "income", "gender"],
        "get_details": [],
    }

    required = required_fields.get(intent, ["age", "income", "gender"])
    return len(get_missing_info(state, required)) == 0


# Hindi field labels (used by ResponseNode)
FIELD_NAMES_HINDI = {
    "age": "उम्र",
    "income": "आय",
    "gender": "लिंग",
    "occupation": "व्यवसाय",
    "category": "श्रेणी",
    "state_location": "राज्य",
    "has_disabilities": "विकलांगता",
    "is_student": "छात्र",
    "marital_status": "वैवाहिक स्थिति",
}


def get_field_name_hindi(field: str) -> str:
    return FIELD_NAMES_HINDI.get(field, field)

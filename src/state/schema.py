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
    
    # User Input
    messages: Annotated[List[Dict[str, str]], operator.add]  # Conversation history
    user_input: str  # Current user input
    
    # User Profile (accumulated information)
    age: Optional[int]
    income: Optional[float]
    gender: Optional[str]
    occupation: Optional[str]
    category: Optional[str]  # SC/ST/OBC/General
    state_location: Optional[str]
    has_disabilities: Optional[bool]
    is_student: Optional[bool]
    marital_status: Optional[str]
    
    # Agent Processing
    current_intent: Optional[str]  # find_schemes, provide_info, apply_scheme, etc.
    missing_information: List[str]  # What info is still needed
    
    # Tool Results
    eligible_schemes: List[Dict[str, Any]]  # Schemes user qualifies for
    selected_scheme_id: Optional[str]  # Scheme user wants to apply for
    application_result: Optional[Dict[str, Any]]  # Application submission result
    
    # Memory & Context
    contradictions: Annotated[List[Dict[str, Any]], operator.add]  # Detected conflicts
    extracted_info: Dict[str, Any]  # Info extracted in current turn
    
    # Control Flow
    next_step: Optional[str]  # Next node to route to
    should_continue: bool  # Whether to continue processing
    error: Optional[str]  # Error message if any
    
    # Metadata
    turn_count: int
    confidence: float  # Confidence in current assessment


class ConversationTurn(TypedDict):
    """Single conversation turn"""
    timestamp: str
    user: str
    agent: str
    intent: str
    tools_used: List[str]
    extracted_info: Dict[str, Any]


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
        next_step="planner",
        should_continue=True,
        error=None,
        turn_count=0,
        confidence=1.0
    )


def update_profile(state: AgentState, field: str, value: Any) -> AgentState:
    """
    Update user profile field and detect contradictions
    
    Args:
        state: Current state
        field: Field to update
        value: New value
        
    Returns:
        Updated state
    """
    old_value = state.get(field)
    
    # Detect contradiction
    if old_value is not None and old_value != value:
        contradiction = {
            'field': field,
            'old_value': old_value,
            'new_value': value,
            'timestamp': datetime.now().isoformat()
        }
        state['contradictions'].append(contradiction)
    
    # Update field
    state[field] = value
    state['extracted_info'][field] = value
    
    return state


def get_missing_info(state: AgentState, required_fields: List[str]) -> List[str]:
    """
    Get list of required fields that are still missing
    
    Args:
        state: Current state
        required_fields: List of required field names
        
    Returns:
        List of missing field names
    """
    missing = []
    for field in required_fields:
        if state.get(field) is None:
            missing.append(field)
    return missing


def is_profile_complete(state: AgentState, intent: str = 'find_schemes') -> bool:
    """
    Check if user profile has enough information for the intent
    
    Args:
        state: Current state
        intent: User intent
        
    Returns:
        True if profile is complete enough
    """
    required_fields = {
        'find_schemes': ['age', 'income', 'gender'],
        'apply_scheme': ['age', 'income', 'gender', 'category'],
        'get_details': []
    }
    
    required = required_fields.get(intent, ['age', 'income', 'gender'])
    missing = get_missing_info(state, required)
    
    return len(missing) == 0


def format_state_summary(state: AgentState) -> str:
    """
    Format state summary for logging/debugging
    
    Args:
        state: Current state
        
    Returns:
        Formatted summary string
    """
    summary = f"""
Agent State Summary:
-------------------
Turn: {state['turn_count']}
Intent: {state.get('current_intent', 'unknown')}
User Profile:
  - Age: {state.get('age', 'N/A')}
  - Income: {state.get('income', 'N/A')}
  - Gender: {state.get('gender', 'N/A')}
  - Occupation: {state.get('occupation', 'N/A')}
  - Category: {state.get('category', 'N/A')}
Missing Info: {state.get('missing_information', [])}
Eligible Schemes: {len(state.get('eligible_schemes', []))}
Contradictions: {len(state.get('contradictions', []))}
Next Step: {state.get('next_step', 'unknown')}
Should Continue: {state.get('should_continue', False)}
"""
    return summary


# Field name mappings for Hindi
FIELD_NAMES_HINDI = {
    'age': 'उम्र',
    'income': 'आय',
    'gender': 'लिंग',
    'occupation': 'व्यवसाय',
    'category': 'श्रेणी',
    'state_location': 'राज्य',
    'has_disabilities': 'विकलांगता',
    'is_student': 'छात्र',
    'marital_status': 'वैवाहिक स्थिति'
}


def get_field_name_hindi(field: str) -> str:
    """Get Hindi name for field"""
    return FIELD_NAMES_HINDI.get(field, field)

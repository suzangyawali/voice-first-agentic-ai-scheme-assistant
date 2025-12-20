import sys
import os
import asyncio


def _ensure_src_on_path():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    src_path = os.path.join(repo_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def test_update_profile_and_contradiction():
    _ensure_src_on_path()
    from state.schema import create_initial_state, update_profile

    state = create_initial_state()
    # First update
    state = update_profile(state, 'age', 25)
    assert state['age'] == 25
    assert state['extracted_info']['age'] == 25

    # Conflicting update
    state = update_profile(state, 'age', 30)
    assert state['age'] == 30
    # One contradiction should be recorded
    assert isinstance(state['contradictions'], list)
    assert len(state['contradictions']) >= 1


def test_get_missing_info_and_profile_complete():
    _ensure_src_on_path()
    from state.schema import create_initial_state, get_missing_info, is_profile_complete

    state = create_initial_state()
    missing = get_missing_info(state, ['age', 'income', 'gender'])
    assert set(missing) == set(['age', 'income', 'gender'])

    # Fill profile
    state['age'] = 28
    state['income'] = 120000
    state['gender'] = 'male'

    assert is_profile_complete(state, intent='find_schemes') is True


def test_format_state_summary_contains_fields():
    _ensure_src_on_path()
    from state.schema import create_initial_state, format_state_summary

    state = create_initial_state()
    state['turn_count'] = 2
    state['age'] = 40
    summary = format_state_summary(state)

    assert 'Turn: 2' in summary
    assert 'Age: 40' in summary or 'उम्र' in summary

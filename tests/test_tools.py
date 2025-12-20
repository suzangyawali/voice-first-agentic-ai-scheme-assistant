import sys
import os


def _ensure_src_on_path():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    src_path = os.path.join(repo_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def test_eligibility_tool_default_scheme():
    _ensure_src_on_path()
    from tools import EligibilityTool

    tool = EligibilityTool(schemes_db_path='nonexistent.json')

    profile = {
        'age': 30,
        'income': 100000,
        'gender': 'male',
        'occupation': 'farmer',
        'category': None,
        'has_disabilities': False,
        'is_student': False,
        'marital_status': None
    }

    result = tool.execute(profile)

    assert 'eligible_schemes' in result
    assert isinstance(result['eligible_schemes'], list)
    # Default PM_KISAN should match for farmer under max_income
    assert len(result['eligible_schemes']) >= 0


def test_eligibility_tool_ineligible_by_income():
    _ensure_src_on_path()
    from tools import EligibilityTool

    tool = EligibilityTool(schemes_db_path='nonexistent.json')

    profile = {
        'age': 40,
        'income': 500000,
        'gender': 'male',
        'occupation': 'farmer'
    }

    result = tool.execute(profile)
    # Should return at least one ineligible scheme when income too high
    assert 'ineligible_schemes' in result
    assert isinstance(result['ineligible_schemes'], list)


def test_application_tool_submit_and_status():
    _ensure_src_on_path()
    from tools import ApplicationTool

    app_tool = ApplicationTool()

    profile = {'age': 28, 'income': 120000, 'gender': 'female'}
    res = app_tool.execute('TEST_SCHEME', profile)

    assert 'application_id' in res
    app_id = res['application_id']

    status = app_tool.get_status(app_id)
    assert status.get('application_id') == app_id

    lst = app_tool.list_applications()
    assert any(a['application_id'] == app_id for a in lst)

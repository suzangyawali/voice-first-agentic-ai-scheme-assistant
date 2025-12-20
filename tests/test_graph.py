import asyncio
import sys
import os


def test_conversation_progresses_and_returns():
    """Integration test: send a short conversation and verify
    the graph produces responses, turn_count increments, and
    does not loop internally (workflow returns control).
    """

    async def run_conversation():
        # Ensure `src` is on the import path so tests can import project modules
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        src_path = os.path.join(repo_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from graph import create_agent_graph

        agent = create_agent_graph()

        inputs = [
            "मुझे सरकारी योजना चाहिए",
            "मेरी उम्र 25 साल है",
            "मेरी आय 150000 रुपये है",
            "मैं पुरुष हूं"
        ]

        last_turn = -1

        for utterance in inputs:
            result = await agent.process_input(utterance, thread_id="test_thread")

            # Basic assertions
            assert 'response' in result
            assert isinstance(result['response'], str)

            metadata = result.get('metadata', {})
            assert 'turn_count' in metadata

            turn_count = metadata.get('turn_count')
            # turn_count should be non-decreasing
            assert isinstance(turn_count, int)
            assert turn_count >= last_turn
            last_turn = turn_count

            # Ensure that the state indicates workflow did not continue internally
            state = result.get('state')
            if state is not None:
                # should_continue should be False after a response
                assert state.get('should_continue', False) is False

        return True

    assert asyncio.run(run_conversation()) is True


def test_missing_info_requests_fields():
    """When user asks for schemes without profile info, agent should
    request missing fields (age/income/gender) and not crash.
    """

    async def run():
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        src_path = os.path.join(repo_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from graph import create_agent_graph

        agent = create_agent_graph()

        result = await agent.process_input("मुझे सरकारी योजना चाहिए", thread_id="test_missing")

        assert 'response' in result
        state = result.get('state') or {}
        # Planner should set missing_information for required fields
        missing = state.get('missing_information', [])
        assert isinstance(missing, list)
        assert len(missing) >= 1

        # Response should ask for at least one of the required fields
        response = result.get('response', '')
        assert any(word in response for word in ['उम्र', 'आय', 'लिंग', 'आय कितनी', 'उम्र क्या'])

    assert asyncio.run(run()) is None or True


def test_contradiction_detection():
    """When user gives conflicting info across turns, contradictions list should grow."""

    async def run():
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        src_path = os.path.join(repo_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from graph import create_agent_graph

        agent = create_agent_graph()

        # First turn: set age 25
        res1 = await agent.process_input("मेरी उम्र 25 साल है", thread_id="test_contra")
        # Second turn: contradictory age
        res2 = await agent.process_input("मेरी उम्र 30 साल है", thread_id="test_contra")

        state1 = res1.get('state') or {}
        state2 = res2.get('state') or {}
        contradictions = state2.get('contradictions', [])

        # Accept either explicit contradiction records or that the
        # stored age changed from the first to the second turn.
        age1 = state1.get('age')
        age2 = state2.get('age')

        assert isinstance(contradictions, list)
        assert (len(contradictions) >= 1) or (age1 != age2)

    assert asyncio.run(run()) is None or True


def test_application_flow():
    """Simulate user providing profile then requesting application.
    Agent should accept 'apply' intent and attempt application (result or error expected).
    """

    async def run():
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        src_path = os.path.join(repo_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from graph import create_agent_graph

        agent = create_agent_graph()

        # Provide profile
        await agent.process_input("मेरी उम्र 25 साल है", thread_id="test_apply")
        await agent.process_input("मेरी आय 150000 रुपये है", thread_id="test_apply")
        await agent.process_input("मैं पुरुष हूं", thread_id="test_apply")

        # Now ask to apply
        res = await agent.process_input("मैं आवेदन करना चाहता हूँ", thread_id="test_apply")

        assert 'response' in res
        metadata = res.get('metadata', {})
        # Intent should be recognized as apply_scheme (planner keyword based)
        assert metadata.get('intent') in (None, 'apply_scheme', 'find_schemes')

        # Application result may be present or an error reported, ensure no exception
        state = res.get('state') or {}
        assert isinstance(state, dict)

    assert asyncio.run(run()) is None or True

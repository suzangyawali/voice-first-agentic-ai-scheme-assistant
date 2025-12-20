"""
LangGraph Workflow
Main agentic workflow using LangGraph
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state.schema import AgentState, create_initial_state
from nodes.planner import planner_node
from nodes.executor import create_executor_node
from nodes.evaluator import (evaluator_node, response_node, 
                              should_continue, route_after_planner, 
                              route_after_evaluator)
from tools.eligibility import EligibilityTool
from tools.application import ApplicationTool

logger = logging.getLogger(__name__)


class VoiceAgentGraph:
    """
    LangGraph-based Voice Agent for Government Schemes
    
    Architecture:
    - Uses LangGraph StateGraph for explicit workflow
    - Planner → Executor → Evaluator → Response loop
    - Persistent memory with checkpointing
    - Native Hindi language support
    """
    
    def __init__(self, schemes_db_path: str = 'data/schemes_hindi.json'):
        """
        Initialize the agent graph
        
        Args:
            schemes_db_path: Path to schemes database
        """
        logger.info("Initializing LangGraph workflow")
        
        # Create tools
        self.eligibility_tool = EligibilityTool(schemes_db_path)
        self.application_tool = ApplicationTool()
        
        # Create executor with tools
        executor_node = create_executor_node(
            self.eligibility_tool,
            self.application_tool
        )
        
        # Build workflow graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        logger.info("Adding workflow nodes...")
        workflow.add_node("planner", planner_node)
        workflow.add_node("executor", executor_node)
        workflow.add_node("evaluator", evaluator_node)
        workflow.add_node("respond", response_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Add edges with routing
        logger.info("Adding workflow edges...")
        
        # Planner can go to executor or directly to respond
        workflow.add_conditional_edges(
            "planner",
            route_after_planner,
            {
                "executor": "executor",
                "respond": "respond"
            }
        )
        
        # Executor always goes to evaluator
        workflow.add_edge("executor", "evaluator")
        
        # Evaluator can go to respond or back to planner
        workflow.add_conditional_edges(
            "evaluator",
            route_after_evaluator,
            {
                "respond": "respond",
                "planner": "planner"
            }
        )
        
        # Response decides if we continue or end
        workflow.add_conditional_edges(
            "respond",
            should_continue,
            {
                "end": END
            }
        )
        
        # Add memory checkpointer for conversation persistence
        memory = MemorySaver()
        
        # Compile the graph with increased recursion limit as safety measure
        logger.info("Compiling workflow...")
        self.app = workflow.compile(checkpointer=memory)
        
        logger.info("LangGraph workflow initialized successfully")
    
    def get_graph_visualization(self) -> str:
        """
        Get REAL LangGraph-generated ASCII visualization
        """
        try:
            graph = self.app.get_graph()
            return graph.draw_ascii()
        except Exception as e:
            return f"Failed to generate graph visualization: {e}"
        
        
    
    async def process_input(self, user_input: str, 
                           thread_id: str = "default") -> dict:
        """
        Process user input through the graph
        
        Args:
            user_input: User's voice input (transcribed to text)
            thread_id: Conversation thread ID for memory
            
        Returns:
            Agent response and metadata
        """
        # Try to load existing conversation state from the checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        input_state = create_initial_state()  # Start with defaults
        
        try:
            state_snapshot = self.app.get_state(config)
            # StateSnapshot has a .values property with the actual state dict
            if state_snapshot and hasattr(state_snapshot, 'values'):
                # Merge the loaded state with defaults (defaults provide any missing fields)
                loaded_values = dict(state_snapshot.values)
                input_state.update(loaded_values)
        except Exception as e:
            logger.info(f"No existing state found or error loading: {e}")

        # Update with current turn's input
        input_state.update({
            "user_input": user_input,
        })

        # Append the incoming user message to history
        messages = input_state.get('messages', [])
        messages = list(messages) if messages is not None else []
        messages.append({"role": "user", "content": user_input})
        input_state['messages'] = messages
        
        # Run the graph
        logger.info(f"Processing input: {user_input[:50]}...")
        
        try:
            # Invoke the graph with recursion limit
            config_with_limit = {
                **config,
                "recursion_limit": 50
            }
            result = await self.app.ainvoke(input_state, config=config_with_limit)
            
            # Extract response
            response_message = result['messages'][-1]['content']
            
            metadata = {
                'intent': result.get('current_intent'),
                'eligible_schemes': len(result.get('eligible_schemes', [])),
                'turn_count': result.get('turn_count', 0),
                'confidence': result.get('confidence', 1.0),
                'extracted_info': result.get('extracted_info', {}),
                'contradictions': len(result.get('contradictions', []))
            }
            
            # Include persistent profile fields in response
            profile = {
                'age': result.get('age'),
                'income': result.get('income'),
                'gender': result.get('gender'),
                'occupation': result.get('occupation'),
                'category': result.get('category'),
                'state_location': result.get('state_location'),
            }
            
            return {
                'response': response_message,
                'metadata': metadata,
                'profile': profile,
                'state': result
            }
        
        except Exception as e:
            logger.error(f"Error processing input: {str(e)}", exc_info=True)
            return {
                'response': 'क्षमा करें, कोई त्रुटि हुई। कृपया पुनः प्रयास करें।',
                'metadata': {'error': str(e)},
                'state': None
            }
    
    async def stream_process(self, user_input: str, 
                            thread_id: str = "default"):
        """
        Stream processing for real-time updates
        
        Args:
            user_input: User input
            thread_id: Thread ID
            
        Yields:
            Intermediate states
        """
        input_state = {
            "user_input": user_input,
            "messages": [{"role": "user", "content": user_input}]
        }
        
        config = {"configurable": {"thread_id": thread_id}}
        
        async for state in self.app.astream(input_state, config=config):
            yield state
    
    def get_state(self, thread_id: str = "default") -> dict:
        """
        Get current conversation state
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Current state
        """
        config = {"configurable": {"thread_id": thread_id}}
        return self.app.get_state(config)
    
    def reset_conversation(self, thread_id: str = "default"):
        """
        Reset conversation for a thread
        
        Args:
            thread_id: Thread ID to reset
        """
        # Create new initial state
        config = {"configurable": {"thread_id": thread_id}}
        initial = create_initial_state()
        self.app.update_state(config, initial)
        logger.info(f"Conversation reset for thread: {thread_id}")


def create_agent_graph(schemes_db_path: str = 'data/schemes_hindi.json') -> VoiceAgentGraph:
    """
    Factory function to create agent graph
    
    Args:
        schemes_db_path: Path to schemes database
        
    Returns:
        Configured VoiceAgentGraph
    """
    return VoiceAgentGraph(schemes_db_path)


# Example usage
if __name__ == '__main__':
    import asyncio
    
    async def main():
        # Create agent
        agent = create_agent_graph()
        
        # Print graph structure
        print(agent.get_graph_visualization())
        
        # Test conversation
        test_inputs = [
            "मुझे सरकारी योजना चाहिए",
            "मेरी उम्र 25 साल है",
            "मेरी आय 150000 रुपये है",
            "मैं पुरुष हूं"
        ]
        
        for user_input in test_inputs:
            print(f"\n👤 User: {user_input}")
            
            result = await agent.process_input(user_input)
            
            print(f"🤖 Agent: {result['response']}")
            print(f"📊 Metadata: {result['metadata']}")
    
    asyncio.run(main())

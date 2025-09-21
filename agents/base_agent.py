"""
Base agent class for LiquidRound multi-agent system.
"""
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.state import State, update_agent_result
from utils.logging import get_logger
from utils.config import config


class BaseAgent(ABC):
    """Base class for all LiquidRound agents."""
    
    def __init__(self, name: str, prompt_file: Optional[str] = None):
        self.name = name
        self.logger = get_logger(f"agent_{name}")
        
        # Load prompt from file if specified
        self.system_prompt = self._load_prompt(prompt_file) if prompt_file else ""
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=config.default_temperature,
            api_key=config.openai_api_key
        )

    
    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt from file."""
        # Get the directory containing this file
        current_dir = Path(__file__).parent
        # Go up one level to the project root, then into prompts
        prompt_path = current_dir.parent / "prompts" / prompt_file
        if prompt_path.exists():
            return prompt_path.read_text().strip()
        else:
            self.logger.warning(f"Prompt file not found: {prompt_path}")
            return ""
    
    async def execute(self, state: State) -> State:
        """Execute the agent with error handling and logging."""
        start_time = time.time()
        
        try:
            self.logger.log_agent_execution(
                agent_name=self.name,
                action="start",
                input_data={"user_query": state["user_query"]},
                metadata={"deal_id": state["deal"]["deal_id"]}
            )
            
            # Update state to show agent is in progress
            state = update_agent_result(
                state, self.name, "in_progress"
            )
            
            # Execute the agent logic
            result = await self._execute_logic(state)
            
            execution_time = time.time() - start_time
            
            # Update state with successful result
            state = update_agent_result(
                state, self.name, "success", result, execution_time
            )
            
            self.logger.log_agent_execution(
                agent_name=self.name,
                action="complete",
                output_data=result,
                execution_time=execution_time,
                metadata={"deal_id": state["deal"]["deal_id"]}
            )
            
            return state
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            
            # Update state with error
            state = update_agent_result(
                state, self.name, "error", None, execution_time, error_message
            )
            
            self.logger.log_error(
                error_type=type(e).__name__,
                error_message=error_message,
                context={
                    "agent_name": self.name,
                    "deal_id": state["deal"]["deal_id"],
                    "execution_time": execution_time
                }
            )
            
            return state
    
    @abstractmethod
    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        """Execute the core agent logic. Must be implemented by subclasses."""
        pass
    
    def _create_messages(self, user_input: str, context: Dict[str, Any] = None) -> List:
        """Create messages for LLM interaction."""
        messages = []
        
        if self.system_prompt:
            # Format system prompt with context if provided
            formatted_prompt = self.system_prompt
            if context:
                try:
                    formatted_prompt = self.system_prompt.format(**context)
                except KeyError as e:
                    self.logger.warning(f"Failed to format prompt with context: {e}")
            
            messages.append(SystemMessage(content=formatted_prompt))
        
        messages.append(HumanMessage(content=user_input))
        
        return messages
    
    async def _call_llm(self, messages: List, **kwargs) -> str:
        """Call the LLM with the given messages."""
        try:
            response = await self.llm.ainvoke(messages, **kwargs)
            return response.content
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise
    
    def _extract_context_from_state(self, state: State) -> Dict[str, Any]:
        """Extract relevant context from state for prompt formatting."""
        return {
            "user_query": state["user_query"],
            "mode": state.get("mode", "unknown"),
            "deal_type": state["deal"]["deal_type"],
            "company_name": state["deal"].get("company_name", ""),
            "industry": state["deal"].get("industry", ""),
            "deal_size": state["deal"].get("deal_size", ""),
            "previous_results": {
                name: result["result"] 
                for name, result in state["agent_results"].items() 
                if result["status"] == "success"
            }
        }

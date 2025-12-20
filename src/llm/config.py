"""LLM Configuration & Manager
Handles LLM provider setup (Groq, Ollama)
"""

import os
import json
import logging
from typing import Dict, Any

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Manages LLM interactions
    Supports multiple providers: Groq (fast API), OpenAI, Ollama, Google Gemini
    
    Note: Groq is the company providing fast LLM API (not Grok by Elon Musk)
    """
    
    def __init__(self, provider: str = 'groq', model: str = 'llama-3.1-8b-instant'):
        """
        Initialize LLM Manager
        
        Args:
            provider: 'groq' (Groq API), 'openai', 'ollama', or 'gemini'
            model: Model name for the provider
        """
        self.provider = provider
        self.model = model
        self.llm = None
        
        self._initialize_llm()
        logger.info(f"LLM Manager initialized: {provider}/{model}")
    
    def _initialize_llm(self):
        """Initialize LLM based on provider (Groq → Ollama only, NO MockLLM)"""
        try:
            if self.provider == 'groq':
                self._init_groq()
            elif self.provider == 'ollama':
                self._init_ollama()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}. Use 'groq' or 'ollama'")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise
    
    def _init_groq(self):
        """Initialize Groq API (not Grok - Groq is the company providing fast LLM API)"""
        try:
            from langchain_openai import ChatOpenAI
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")
            
            # Groq API with OpenAI-compatible endpoint
            # Using llama-3.1-8b-instant (fast model available on Groq)
            self.llm = ChatOpenAI(
                model='llama-3.1-8b-instant',
                temperature=0.7,
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            logger.info("✅ Groq API initialized (llama-3.1-8b-instant)")
        except Exception as e:
            logger.error(f"Groq init failed: {e}")
            self._init_ollama()
    
    def _init_ollama(self):
        """Initialize Ollama (local LLM - qwen2.5 or llama3)"""
        try:
            from langchain_community.llms import Ollama
            self.llm = Ollama(
                model=self.model,
                temperature=0.7,
                base_url='http://localhost:11434'
            )
            logger.info(f"✅ Ollama {self.model} initialized")
        except Exception as e:
            logger.error(f"Ollama init failed: {e}")
            logger.error(f"Install Ollama: brew install ollama")
            logger.error(f"Start Ollama: ollama serve")
            logger.error(f"Pull model: ollama pull {self.model}")
            raise
    
    def _init_mock(self):
        """Initialize mock LLM for testing"""
        self.llm = MockLLM()
        logger.warning("⚠️ Using MockLLM - for testing only")
    
    def invoke(self, prompt: str) -> str:
        """
        Send prompt to LLM and get response
        
        Args:
            prompt: Input prompt (in Hindi)
            
        Returns:
            LLM response (in Hindi)
        """
        try:
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
                if hasattr(response, 'content'):
                    return response.content
                return str(response)
            else:
                return str(self.llm.invoke(prompt))
        except Exception as e:
            logger.error(f"LLM invoke error: {e}")
            return "क्षमा करें, कोई त्रुटि हुई। कृपया पुनः प्रयास करें।"
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed JSON dict
        """
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse JSON: {e}")
        
        return {}


# Global LLM instance
_llm_manager = None


def get_llm_manager(provider: str = 'groq') -> LLMManager:
    """Get or create global LLM manager (Groq or Ollama)"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager(provider=provider)
    return _llm_manager

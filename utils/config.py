"""
Configuration management for LiquidRound system.
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for LiquidRound."""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.polygon_api_key = os.getenv("POLYGON_API_KEY")
        self.exa_api_key = os.getenv("EXA_API_KEY")
        
        # Model settings
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.default_temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment.lower() == "production"
        
        # Validate required keys
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required configuration is present."""
        required_keys = ["openai_api_key"]
        missing_keys = []
        
        for key in required_keys:
            if not getattr(self, key):
                missing_keys.append(key.upper())
        
        if missing_keys:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_keys)}"
            )
    
    def get_model_config(self, model: Optional[str] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Get model configuration."""
        return {
            "model": model or self.default_model,
            "temperature": temperature or self.default_temperature,
            "api_key": self.openai_api_key
        }
    
    def get_api_config(self, service: str) -> Dict[str, Any]:
        """Get API configuration for a specific service."""
        configs = {
            "polygon": {
                "api_key": self.polygon_api_key,
                "base_url": "https://api.polygon.io"
            },
            "exa": {
                "api_key": self.exa_api_key,
                "base_url": "https://api.exa.ai"
            },
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.default_model,
                "temperature": self.default_temperature
            }
        }
        
        return configs.get(service, {})
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


# Global config instance
config = Config()

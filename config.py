# config.py - Configuration management for Restaurant Assistant
import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Configuration for agent STT, LLM, TTS, and VAD settings"""
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    
    # Deepgram Configuration
    deepgram_api_key: str
    
    # Cartesia Configuration
    cartesia_api_key: str
    cartesia_voice_id: Optional[str] = None
    
    # Silero VAD (no API key needed)
    vad_model: str = "silero"
    
    # Firebase Configuration
    firebase_service_account_path: str = "service.json"

def load_config() -> AgentConfig:
    """Load configuration from environment variables"""
    
    # Required API keys
    openai_api_key = os.getenv("OPENAI_API_KEY")
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY") 
    cartesia_api_key = os.getenv("CARTESIA_API_KEY")
    
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    if not deepgram_api_key:
        raise ValueError("DEEPGRAM_API_KEY environment variable is required")
    if not cartesia_api_key:
        raise ValueError("CARTESIA_API_KEY environment variable is required")
    
    # Optional configurations with defaults
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    cartesia_voice_id = os.getenv("CARTESIA_VOICE_ID")
    firebase_service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service.json")
    
    logger.info(f"Loaded config - OpenAI model: {openai_model}")
    
    return AgentConfig(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        deepgram_api_key=deepgram_api_key,
        cartesia_api_key=cartesia_api_key,
        cartesia_voice_id=cartesia_voice_id,
        firebase_service_account_path=firebase_service_account
    )

def validate_config(config: AgentConfig) -> bool:
    """Validate that all required configuration is present"""
    required_fields = [
        config.openai_api_key,
        config.deepgram_api_key, 
        config.cartesia_api_key
    ]
    
    if not all(required_fields):
        logger.error("Missing required API keys in configuration")
        return False
        
    logger.info("Configuration validation passed")
    return True
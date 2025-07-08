# config.py - Configuration management for Restaurant Assistant
import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Configuration for agent STT, LLM, TTS, and VAD settings"""
    # Required fields (no defaults) - must come first
    openai_api_key: str
    deepgram_api_key: str
    cartesia_api_key: str
    
    # Optional fields with defaults - must come after required fields
    openai_model: str = "gpt-4o-mini"
    cartesia_voice_id: Optional[str] = None
    vad_model: str = "silero"
    firebase_service_account_path: str = "service.json"
    sip_phone_number: Optional[str] = None
    sip_trunk_address: Optional[str] = None
    sip_username: Optional[str] = None
    sip_password: Optional[str] = None
    sip_outbound_trunk_id: Optional[str] = None

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
    
    # SIP configurations
    sip_phone_number = os.getenv("SIP_PHONE_NUMBER")
    sip_trunk_address = os.getenv("SIP_TRUNK_ADDRESS")
    sip_username = os.getenv("SIP_USERNAME")
    sip_password = os.getenv("SIP_PASSWORD")
    sip_outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
    
    logger.info(f"Loaded config - OpenAI model: {openai_model}")
    
    return AgentConfig(
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        deepgram_api_key=deepgram_api_key,
        cartesia_api_key=cartesia_api_key,
        cartesia_voice_id=cartesia_voice_id,
        firebase_service_account_path=firebase_service_account,
        sip_phone_number=sip_phone_number,
        sip_trunk_address=sip_trunk_address,
        sip_username=sip_username,
        sip_password=sip_password,
        sip_outbound_trunk_id=sip_outbound_trunk_id
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
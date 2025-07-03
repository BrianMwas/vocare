# main.py - LiveKit Restaurant Assistant Entrypoint with SIP Support
import logging
from livekit.agents import JobContext, WorkerOptions, AgentSession, cli, AutoSubscribe
from livekit.agents.sip import SipContext
from app.models.restaurant import UserData
from manager import FirebaseManager
from assistant import IntentClassifierAgent, OrderAgent, ReservationAgent, ConfirmationAgent
from config import load_config, validate_config

logger = logging.getLogger(__name__)

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the restaurant assistant with SIP support"""
    
    # Load and validate configuration
    config = load_config()
    if not validate_config(config):
        raise ValueError("Invalid configuration - check your API keys")

    # Initialize Firebase manager
    firebase = FirebaseManager(config.firebase_service_account_path)
    
    # Check if this is a SIP call
    is_sip_call = ctx.job.job_type == "sip_call"
    
    if is_sip_call:
        # Handle SIP telephony call
        sip_ctx = SipContext(ctx)
        call_info = {
            "call_id": sip_ctx.call_info.call_id,
            "caller_number": sip_ctx.call_info.from_number,
            "called_number": sip_ctx.call_info.to_number,
            "call_type": "inbound_sip"
        }
        logger.info(f"📞 Incoming SIP call from {call_info['caller_number']} to {call_info['called_number']}")
    else:
        # Handle regular LiveKit room connection
        call_info = {
            "call_id": ctx.room.name,
            "caller_number": "web_user",
            "called_number": "restaurant",
            "call_type": "web_session"
        }
        logger.info(f"🌐 Web session started: {call_info['call_id']}")
    
    # Create UserData instance for the session
    userdata = UserData(
        call_id=call_info["call_id"],
        caller_number=call_info["caller_number"],
        agent_id="restaurant-assistant",
        session_id=call_info["call_id"],
        intent="incoming_call"
    )

    # Create all agent instances with configuration
    intent_classifier = IntentClassifierAgent(
        chat_ctx=None,  # Will be set by session
        firebase=firebase,
        userdata=userdata,
        config=config
    )
    
    order_agent = OrderAgent(
        chat_ctx=None,  # Will be set by session
        firebase=firebase,
        userdata=userdata,
        config=config
    )
    
    reservation_agent = ReservationAgent(
        chat_ctx=None,  # Will be set by session
        firebase=firebase,
        userdata=userdata,
        config=config
    )
    
    confirmation_agent = ConfirmationAgent(
        chat_ctx=None,  # Will be set by session
        firebase=firebase,
        userdata=userdata,
        config=config
    )

    # Register all agents in the userdata (if your UserData supports personas)
    if hasattr(userdata, 'personas'):
        userdata.personas.update({
            "intent_classifier": intent_classifier,
            "order": order_agent,
            "reservation": reservation_agent,
            "confirmation": confirmation_agent
        })

    # Create and start the agent session
    session = AgentSession[UserData](userdata=userdata)

    # Connect to room with appropriate subscription settings
    if is_sip_call:
        # For SIP calls, subscribe to audio only
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info("📞 Connected to SIP call - audio only mode")
    else:
        # For web sessions, subscribe to everything
        await ctx.connect()
        logger.info("🌐 Connected to web session")

    # Start the agent session
    await session.start(
        agent=intent_classifier,  # Start with the intent classifier
        room=ctx.room,
    )

    # Log call completion
    if is_sip_call:
        logger.info(f"📞 SIP call completed: {call_info['call_id']}")
    else:
        logger.info(f"🌐 Web session completed: {call_info['call_id']}")


if __name__ == "__main__":
    # Configure CLI options for SIP support
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        # Enable SIP support
        sip_enabled=True,
        # Configure for production deployment
        max_retry_count=3,
        # Add logging
        log_level="INFO"
    ))

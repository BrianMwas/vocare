# main.py - LiveKit Restaurant Assistant Entrypoint with SIP Support
import logging
from livekit.agents import JobContext, WorkerOptions, AgentSession, cli, AutoSubscribe
from app.models.restaurant import UserData
from manager import FirebaseManager
from assistant import IntentClassifierAgent
from config import load_config, validate_config
from error_handlers import RestaurantErrorHandler, SipCallHandler

logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the restaurant assistant with SIP support"""
    
    try:
        # Load and validate configuration
        config = load_config()
        if not validate_config(config):
            raise ValueError("Invalid configuration - check your API keys")

        # Initialize Firebase manager
        firebase = FirebaseManager(config.firebase_service_account_path)
        
        # Initialize error handlers
        error_handler = RestaurantErrorHandler(firebase)
        sip_handler = SipCallHandler(firebase)
        
        # Set up SIP trunk on first run
        await sip_handler.setup_sip_trunk(config)
        
        # Create call info (SIP info automatically handled by LiveKit when sip_enabled=True)
        call_info = {
            "call_id": ctx.room.name,
            "caller_number": getattr(ctx.job, 'sip', {}).get('from_number', 'unknown') if hasattr(ctx.job, 'sip') else "web_user",
            "called_number": getattr(ctx.job, 'sip', {}).get('to_number', 'restaurant') if hasattr(ctx.job, 'sip') else "restaurant",
            "call_type": "sip_call" if hasattr(ctx.job, 'sip') and ctx.job.sip else "web_session"
        }
        
        logger.info(f"📞 Session started: {call_info['call_type']} - {call_info['caller_number']} to {call_info['called_number']}")
    
        # Create UserData instance for the session
        userdata = UserData(
            call_id=call_info["call_id"],
            caller_number=call_info["caller_number"],
            agent_id="restaurant-assistant",
            session_id=call_info["call_id"],
            intent="incoming_call"
        )

        # Create only the initial agent - others will be created during handoffs
        intent_classifier = IntentClassifierAgent(
            chat_ctx=None,  # Will be set by session
            firebase=firebase,
            userdata=userdata,
            config=config
        )

        # Start the agent session
        session = AgentSession[UserData](userdata=userdata)

        # Connect to room (LiveKit automatically handles SIP vs web differences)
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info(f"🔗 Connected to room: {ctx.room.name}")

        # Start the agent session with error handling
        try:
            await session.start(
                agent=intent_classifier,  # Start with the intent classifier
                room=ctx.room,
            )
            
            # Always greet first for inbound calls (web sessions and inbound SIP)
            await session.generate_reply(
                instructions="Greet the user warmly and offer your assistance."
            )
            
        except Exception as e:
            # Handle agent session errors
            logger.error(f"Agent session error: {e}")
            await error_handler.handle_agent_error(e, session.run_context, intent_classifier)
            raise

        # Log session completion
        logger.info(f"✅ {call_info['call_type']} completed: {call_info['call_id']}")
            
    except Exception as e:
        logger.error(f"Critical error in entrypoint: {e}")
        raise


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

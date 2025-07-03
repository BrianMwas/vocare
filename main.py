# main.py - LiveKit Restaurant Assistant Entrypoint
import logging
from livekit.agents import JobContext, WorkerOptions, AgentSession, cli
from app.models.restaurant import UserData
from manager import FirebaseManager
from assistant import IntentClassifierAgent, OrderAgent, ReservationAgent, ConfirmationAgent
from config import load_config, validate_config

logger = logging.getLogger(__name__)

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the restaurant assistant"""
    await ctx.connect()

    # Load and validate configuration
    config = load_config()
    if not validate_config(config):
        raise ValueError("Invalid configuration - check your API keys")

    # Initialize Firebase manager
    firebase = FirebaseManager(config.firebase_service_account_path)
    
    # Create UserData instance for the session
    userdata = UserData(
        call_id=ctx.room.name,  # Use room name as call ID
        agent_id="restaurant-assistant",
        session_id=ctx.room.name
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

    await session.start(
        agent=intent_classifier,  # Start with the intent classifier
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

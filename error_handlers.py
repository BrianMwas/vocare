# error_handlers.py - Error handling for the restaurant AI assistant
import logging
import traceback
from datetime import datetime
from typing import Dict
from livekit.agents import Agent, RunContext, JobContext
from livekit import api
from livekit.protocol.sip import ListSIPInboundTrunkRequest, SIPInboundTrunkInfo
from app.models.restaurant import UserData
from config import AgentConfig
from manager import FirebaseManager

logger = logging.getLogger(__name__)


class RestaurantErrorHandler:
    """Handles errors gracefully in production"""
    
    def __init__(self, firebase_manager: FirebaseManager):
        self.firebase = firebase_manager
        
    async def handle_agent_error(self, error: Exception, context: RunContext[UserData], agent: Agent) -> str:
        """Handle agent errors gracefully"""
        error_id = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Log detailed error
        logger.error(f"Agent error {error_id}: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Save error to Firebase for debugging
        await self._log_error_to_firebase(error_id, error, context, agent)
        
        # Return user-friendly message
        if isinstance(error, ConnectionError):
            return "I'm having trouble with my connection. Let me try to help you in a different way."
        elif isinstance(error, TimeoutError):
            return "Sorry, that's taking longer than expected. Could you repeat your request?"
        elif "openai" in str(error).lower():
            return "I'm having trouble processing that right now. Could you try asking in a different way?"
        elif "firebase" in str(error).lower():
            return "I'm having trouble saving that information. Don't worry, I can still help you."
        else:
            return "I apologize, I'm having a small technical issue. How else can I help you today?"
    
    async def handle_sip_error(self, error: Exception, call_info: dict) -> bool:
        """Handle SIP connection errors"""
        logger.error(f"SIP error for call {call_info.get('call_id', 'unknown')}: {error}")
        
        # Log to Firebase
        try:
            await self.firebase.call_logs_collection.add({
                "call_id": call_info.get("call_id", "unknown"),
                "error_type": "sip_error",
                "error_message": str(error),
                "timestamp": self.firebase.db.SERVER_TIMESTAMP,
                "caller_number": call_info.get("caller_number", "unknown")
            })
        except:
            pass  # Don't fail on logging errors
        
        # Return True if we should retry, False if fatal
        if "authentication" in str(error).lower():
            return False  # Don't retry auth errors
        elif "network" in str(error).lower():
            return True   # Retry network errors
        else:
            return False  # Don't retry unknown errors
    
    async def _log_error_to_firebase(self, error_id: str, error: Exception, context: RunContext[UserData], agent: Agent):
        """Log detailed error information to Firebase"""
        try:
            error_data = {
                "error_id": error_id,
                "timestamp": self.firebase.db.SERVER_TIMESTAMP,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "agent_type": agent.__class__.__name__,
                "user_data": {
                    "customer_name": getattr(context.userdata, 'customer_name', ''),
                    "customer_phone": getattr(context.userdata, 'customer_phone', ''),
                    "call_id": getattr(context.userdata, 'call_id', ''),
                    "intent": getattr(context.userdata, 'intent', '')
                },
                "stack_trace": traceback.format_exc()
            }
            
            await self.firebase.db.collection('errors').add(error_data)
            
        except Exception as e:
            logger.error(f"Failed to log error to Firebase: {e}")


class SipCallHandler:
    """Handles SIP call setup and teardown"""
    
    def __init__(self, firebase_manager: FirebaseManager):
        self.firebase = firebase_manager
        self.livekit_api = None
        
    async def setup_sip_trunk(self, config: AgentConfig):
        """Set up SIP inbound trunk for handling phone calls"""
        if not config.sip_phone_number:
            logger.warning("No SIP phone number configured, skipping SIP trunk setup")
            return
            
        try:
            if not self.livekit_api:
                self.livekit_api = api.LiveKitAPI()
            
            # Check if trunk already exists
            existing_trunk = await self._find_existing_trunk(config.sip_phone_number)
            
            if existing_trunk:
                logger.info(f"📞 SIP trunk already exists: {existing_trunk.name}")
                return existing_trunk
            
            # Create new inbound trunk
            trunk = api.SIPInboundTrunkInfo(
                name="Restaurant Assistant Trunk",
                numbers=[config.sip_phone_number],
                krisp_enabled=True,
            )
            
            request = api.CreateSIPInboundTrunkRequest(trunk=trunk)
            trunk_response = await self.livekit_api.sip.create_sip_inbound_trunk(request)
            
            logger.info(f"📞 SIP inbound trunk created: {trunk_response.trunk.name}")
            
            # Create outbound trunk for making calls
            if config.sip_trunk_address and config.sip_username and config.sip_password:
                outbound_trunk = api.SIPOutboundTrunkInfo(
                    name="Restaurant Assistant Outbound Trunk",
                    address=config.sip_trunk_address,
                    transport="udp",
                    numbers=[config.sip_phone_number],
                    auth_username=config.sip_username,
                    auth_password=config.sip_password,
                )
                
                outbound_request = api.CreateSIPOutboundTrunkRequest(trunk=outbound_trunk)
                outbound_response = await self.livekit_api.sip.create_sip_outbound_trunk(outbound_request)
                
                logger.info(f"📞 SIP outbound trunk created: {outbound_response.trunk.name}")
            else:
                logger.warning("Outbound SIP configuration incomplete, skipping outbound trunk setup")
            
            return trunk_response.trunk
            
        except Exception as e:
            logger.error(f"Failed to setup SIP trunk: {e}")
            raise

    async def _find_existing_trunk(self, phone_number: str):
        """Find existing trunk with the given phone number"""
        try:
            trunks = await self.livekit_api.sip.list_sip_inbound_trunk(
                ListSIPInboundTrunkRequest()
            )
            
            for trunk in trunks.items:
                if phone_number in trunk.numbers:
                    return trunk
            return None
            
        except Exception as e:
            logger.warning(f"Failed to list existing trunks: {e}")
            return None

    async def list_sip_trunks(self):
        """List all SIP inbound trunks"""
        try:
            if not self.livekit_api:
                self.livekit_api = api.LiveKitAPI()
            
            trunks = await self.livekit_api.sip.list_sip_inbound_trunk(
                ListSIPInboundTrunkRequest()
            )
            
            logger.info(f"Found {len(trunks.items)} SIP trunks")
            for trunk in trunks.items:
                logger.info(f"  - {trunk.name}: {trunk.numbers}")
            
            return trunks.items
            
        except Exception as e:
            logger.error(f"Failed to list SIP trunks: {e}")
            raise

    async def update_sip_trunk_fields(self, trunk_id: str, **fields):
        """Update specific fields of an SIP trunk"""
        try:
            if not self.livekit_api:
                self.livekit_api = api.LiveKitAPI()
            
            trunk = await self.livekit_api.sip.update_sip_inbound_trunk_fields(
                trunk_id=trunk_id,
                **fields
            )
            
            logger.info(f"📞 SIP trunk updated: {trunk.name}")
            return trunk
            
        except Exception as e:
            logger.error(f"Failed to update SIP trunk: {e}")
            raise

    async def replace_sip_trunk(self, trunk_id: str, new_trunk_info: SIPInboundTrunkInfo):
        """Completely replace an SIP trunk"""
        try:
            if not self.livekit_api:
                self.livekit_api = api.LiveKitAPI()
            
            trunk = await self.livekit_api.sip.update_sip_inbound_trunk(trunk_id, new_trunk_info)
            
            logger.info(f"📞 SIP trunk replaced: {trunk.name}")
            return trunk
            
        except Exception as e:
            logger.error(f"Failed to replace SIP trunk: {e}")
            raise

    async def make_outbound_call(self, to_number: str, room_name: str = None):
        """Make an outbound SIP call"""
        try:
            if not self.livekit_api:
                self.livekit_api = api.LiveKitAPI()
            
            if not room_name:
                room_name = f"outbound_call_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create SIP dispatch rule for outbound call
            dispatch_rule = api.SIPDispatchRule(
                rule=api.SIPDispatchRuleIndividual(
                    room_name=room_name,
                    pin=""  # No PIN required
                )
            )
            
            request = api.CreateSIPParticipantRequest(
                sip_call_to=to_number,
                room_name=room_name,
                participant_identity="restaurant_assistant",
                dispatch_rules=[dispatch_rule]
            )
            
            response = await self.livekit_api.sip.create_sip_participant(request)
            
            logger.info(f"📞 Outbound call initiated to {to_number} in room {room_name}")
            
            return {
                "call_id": response.participant.identity,
                "room_name": room_name,
                "to_number": to_number,
                "status": "initiated"
            }
            
        except Exception as e:
            logger.error(f"Failed to make outbound call: {e}")
            raise

    async def close(self):
        """Close the LiveKit API connection"""
        if self.livekit_api:
            await self.livekit_api.aclose()
            self.livekit_api = None
        
    async def handle_sip_call(self, ctx: JobContext) -> Dict:
        """Extract call information from SIP JobContext"""
        try:
            # Get SIP call information from JobContext
            call_info = {
                "call_id": ctx.job.id,
                "caller_number": self._normalize_phone(ctx.job.sip.from_number),
                "called_number": self._normalize_phone(ctx.job.sip.to_number),
                "call_type": "inbound_sip",
                "sip_headers": dict(ctx.job.sip.headers) if ctx.job.sip.headers else {}
            }
            
            logger.info(f"📞 SIP call from {call_info['caller_number']} to {call_info['called_number']}")
            
            # Log call start
            await self._log_call_start(call_info)
            
            return call_info
            
        except Exception as e:
            logger.error(f"Error handling SIP call: {e}")
            raise
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number format"""
        if not phone:
            return "unknown"
            
        # Remove special characters
        clean = ''.join(filter(str.isdigit, phone))
        
        # Add country code if needed
        if len(clean) == 10:
            return f"+1{clean}"
        elif len(clean) == 11 and clean.startswith('1'):
            return f"+{clean}"
        
        return phone
    
    async def _log_call_start(self, call_info: Dict):
        """Log call start to Firebase"""
        try:
            call_log = {
                "call_id": call_info["call_id"],
                "caller_number": call_info["caller_number"],
                "called_number": call_info["called_number"],
                "start_time": self.firebase.db.SERVER_TIMESTAMP,
                "call_type": call_info["call_type"],
                "status": "started"
            }
            
            await self.firebase.call_logs_collection.add(call_log)
            
        except Exception as e:
            logger.warning(f"Failed to log call start: {e}")
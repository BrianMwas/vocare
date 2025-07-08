

import logging
from app.models.restaurant import UserData
from manager import FirebaseManager

from livekit.plugins import openai, silero, deepgram, cartesia
from livekit.agents import Agent, function_tool, RunContext, ChatContext, ChatMessage, get_job_context
from livekit import api
from config import AgentConfig
from shared_tools import update_customer_name, update_customer_phone, update_customer_email, add_special_instructions, get_customer_summary, check_loyalty_status

logger = logging.getLogger(__name__)

class BaseRestaurantAgent(Agent):
    """Base agent that knows how to update and check user data"""

    def __init__(self, chat_ctx: ChatContext, firebase: FirebaseManager, userdata: UserData, config: AgentConfig):
        self.firebase = firebase
        self.userdata = userdata
        self.config = config
        
        # Configure agent with STT, LLM, TTS, VAD and shared tools
        super().__init__(
            chat_ctx=chat_ctx,
            stt=deepgram.STT(api_key=config.deepgram_api_key),
            llm=openai.LLM(
                model=config.openai_model,
                api_key=config.openai_api_key
            ),
            tts=cartesia.TTS(
                api_key=config.cartesia_api_key,
                voice=config.cartesia_voice_id
            ),
            vad=silero.VAD.load(),
            tools=[
                update_customer_name,
                update_customer_phone, 
                update_customer_email,
                add_special_instructions,
                get_customer_summary,
                check_loyalty_status,
                self.end_call
            ]
        )
        
    def _set_room_agent_tag(self, agent_name: str):
        try:
            ctx = get_job_context()
            if ctx and ctx.room and ctx.room.isconnected:
               ctx.api.room.update_room_metadata(ctx.room.sid, {"agent": agent_name})
        except Exception as e:
            logger.warning(f"Failed to set agent metadata: {e}")

    async def on_enter(self):
        """Called when agent becomes active - manage context and greet user"""
        agent_name = self.__class__.__name__
        logger.info(f"Entering {agent_name}")

        userdata: UserData = self.session.userdata
        self._set_room_agent_tag(agent_name)

        chat_ctx = self.chat_ctx.copy()

        # Merge context from previous agent if exists
        if hasattr(userdata, 'prev_agent') and userdata.prev_agent:
            items_copy = self._truncate_chat_ctx(
                userdata.prev_agent.chat_ctx.items, keep_function_call=True
            )
            existing_ids = {item.id for item in chat_ctx.items}
            items_copy = [item for item in items_copy if item.id not in existing_ids]
            chat_ctx.items.extend(items_copy)

        # Add system message with current context
        chat_ctx.add_message(
            role="system",
            content=f"You are the {agent_name}. {self.instructions} Current session: {userdata.summarize()}"
        )
        await self.update_chat_ctx(chat_ctx)
        
        # Generate appropriate greeting
        await self.session.generate_reply(
            instructions="Greet the user warmly based on your role and current context.",
        )

    def _truncate_chat_ctx(
        self,
        items: list,
        keep_last_n_messages: int = 6,
        keep_system_message: bool = False,
        keep_function_call: bool = False,
    ) -> list:
        """Truncate the chat context to keep the last n messages."""
        def _valid_item(item) -> bool:
            if not keep_system_message and item.type == "message" and item.role == "system":
                return False
            if not keep_function_call and item.type in ["function_call", "function_call_output"]:
                return False
            return True

        new_items = []
        for item in reversed(items):
            if _valid_item(item):
                new_items.append(item)
            if len(new_items) >= keep_last_n_messages:
                break
        new_items = new_items[::-1]

        # Remove orphaned function calls at the beginning
        while new_items and new_items[0].type in ["function_call", "function_call_output"]:
            new_items.pop(0)

        return new_items

    async def _transfer_to_agent(self, name: str, context: RunContext) -> Agent:
        """Transfer to another agent while preserving context"""
        userdata = context.userdata
        current_agent = context.session.current_agent
        if hasattr(userdata, 'personas') and name in userdata.personas:
            next_agent = userdata.personas[name]
            userdata.prev_agent = current_agent
            return next_agent
        else:
            logger.error(f"Agent {name} not found in personas")
            return current_agent

    async def on_exit(self):
        """Called before agent handoff - say goodbye"""
        # Generate appropriate transition message
        await self.session.generate_reply(
            instructions="Let the user know you're transferring them to a specialist who can better help them.",
        )

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Called after user's turn - fetch relevant information from Firebase and enrich context"""
        message_text = new_message.text_content()
        
        # Look up customer information from Firebase based on user's message
        customer_info = await self._lookup_customer_info(message_text)
        
        if customer_info:
            turn_ctx.add_message(
                role="assistant", 
                content=f"Customer information found: {customer_info}"
            )
            # Persist the enriched context
            await self.update_chat_ctx(turn_ctx)

    async def _lookup_customer_info(self, message_text: str) -> str:
        """Look up customer information from Firebase based on message content"""
        import re
        
        # Extract phone numbers from message
        phone_matches = re.findall(r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})', message_text)
        
        # Extract email addresses from message
        email_matches = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message_text)
        
        info_parts = []
        
        # Look up by phone number
        if phone_matches:
            try:
                phone = phone_matches[0]
                customer_history = await self.firebase.get_customer_order_history(phone)
                if customer_history:
                    info_parts.append(f"Found {len(customer_history)} previous orders for {phone}")
                    # Get customer preferences
                    preferences = await self.firebase.get_customer_preferences(phone)
                    if preferences:
                        info_parts.append(f"Customer preferences: {preferences}")
            except Exception as e:
                logger.warning(f"Failed to lookup customer by phone: {e}")
        
        # Look up by email
        if email_matches:
            try:
                email = email_matches[0]
                # You could add email-based lookup here if your Firebase supports it
                info_parts.append(f"Email provided: {email}")
            except Exception as e:
                logger.warning(f"Failed to lookup customer by email: {e}")
        
        return " | ".join(info_parts) if info_parts else ""

    async def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        import re
        # Simple phone validation - adjust pattern as needed
        phone_pattern = r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
        return bool(re.match(phone_pattern, phone.strip()))

    async def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))

    def _handoff_if_done(self):
        # Default: no handoff, override in child if needed
        return None

    @function_tool()
    async def end_call(self) -> None:
        """Use this tool when the caller's request is outside the restaurant's scope (e.g., asking about jobs, services we don't offer, etc.)"""
        await self.session.say("Thank you for your time, have a wonderful day.")
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(api.DeleteRoomRequest(room=job_ctx.room.name))


class IntentClassifierAgent(BaseRestaurantAgent):
    def __init__(self, chat_ctx, firebase, userdata: UserData, config: AgentConfig):
        super().__init__(chat_ctx, firebase, userdata, config)
        
        # Get menu information from Firebase
        menu_text = firebase.get_menu_text()
        
        self.instructions = (
            f"You're a friendly cafe staff member. Listen to what the customer wants and help them "
            f"in a warm, natural way. If they want to order food, make a reservation, or just ask questions, "
            f"respond conversationally like you're having a real conversation with a regular customer.\n\n"
            f"Our Menu Today:\n{menu_text}\n\n"
            f"GUIDELINES:\n"
            f"- If they want to order food → use intent_is_order\n"
            f"- If they want to make a reservation → use intent_is_reservation\n"
            f"- Answer simple questions about menu/hours yourself\n"
            f"- Use the shared tools to capture customer information\n"
            f"- Be warm and welcoming, especially to returning customers"
        )
        
    @function_tool()
    async def intent_is_order(self, context: RunContext[UserData]):
        context.userdata.intent = "order"
        return OrderAgent(chat_ctx=self.session._chat_ctx, firebase=self.firebase, userdata=context.userdata, config=self.config)

    @function_tool()
    async def intent_is_reservation(self, context: RunContext[UserData]):
        context.userdata.intent = "reservation"
        return ReservationAgent(chat_ctx=self.session._chat_ctx, firebase=self.firebase, userdata=context.userdata, config=self.config)
    
    

class OrderAgent(BaseRestaurantAgent):
    def __init__(self, chat_ctx, firebase, userdata: UserData, config: AgentConfig):
        super().__init__(chat_ctx, firebase, userdata, config)
        
        # Get menu information from Firebase
        menu_text = firebase.get_menu_text()
        
        self.instructions = (
            f"You're a friendly cafe staff member taking orders. Chat naturally with customers about "
            f"what they'd like to eat or drink. If you need their name or phone for the order, ask casually. "
            f"Only ask for information you actually need - don't interrogate them. Be conversational and helpful, "
            f"like you're talking to a neighbor who stopped by for coffee.\n\n"
            f"Our Menu Today:\n{menu_text}\n\n"
            f"GUIDELINES:\n"
            f"- Help customers choose from our available menu items\n"
            f"- Ask about quantity and any modifications\n"
            f"- Use shared tools to collect customer info (name, phone)\n"
            f"- When order is complete, use finalize_order to proceed to confirmation\n"
            f"- Suggest popular items if customers seem unsure\n"
            f"- Mention loyalty points for returning customers"
        )

    @function_tool()
    async def add_item(self, context: RunContext[UserData], item: str, quantity: int):
        context.userdata.current_order.append({"item": item, "quantity": quantity})
        return self._handoff_if_done()

    @function_tool()
    async def set_payment_method(self, context: RunContext[UserData], method: str):
        context.userdata.payment_method = method
        return self._handoff_if_done()

    @function_tool()
    async def finalize_order(self, context: RunContext[UserData]):
        """Hand off to ConfirmationAgent to review order details"""
        return ConfirmationAgent(
            chat_ctx=self.session._chat_ctx,
            firebase=self.firebase,
            userdata=context.userdata,
            config=self.config
        )

    def _handoff_if_done(self):
        """Check if enough info is collected"""
        if self.userdata.customer_name and self.userdata.customer_phone and self.userdata.current_order:
            return "You may now confirm the order."
        return None
    

class ReservationAgent(BaseRestaurantAgent):
    def __init__(self, chat_ctx, firebase, userdata: UserData, config: AgentConfig):
        super().__init__(chat_ctx, firebase, userdata, config)
        self.instructions = (
            "You're a friendly cafe staff member helping with table reservations. Chat naturally about "
            "when they'd like to come in and how many people. Ask for their name and phone in a casual way "
            "when you need it. Be warm and welcoming, like you're genuinely excited to have them visit."
        )

    @function_tool()
    async def set_reservation_details(self, context: RunContext[UserData], date: str, time: str, party_size: int):
        context.userdata.reservation_date = date
        context.userdata.reservation_time = time
        context.userdata.party_size = party_size
        return self._handoff_if_done()

    @function_tool()
    async def confirm_reservation(self, context: RunContext[UserData]):
        """Hand off to ConfirmationAgent to review reservation details"""
        return ConfirmationAgent(chat_ctx=self.session._chat_ctx, firebase=self.firebase, userdata=context.userdata, config=self.config)

    def _handoff_if_done(self):
        if (
            self.userdata.customer_name
            and self.userdata.customer_phone
            and self.userdata.reservation_date
            and self.userdata.reservation_time
            and self.userdata.party_size > 0
        ):
            return "You can now use `confirm_reservation` to save this."
        return None

class ConfirmationAgent(BaseRestaurantAgent):
    def __init__(self, chat_ctx, firebase, userdata: UserData, config: AgentConfig):
        super().__init__(chat_ctx, firebase, userdata, config)
        self.instructions = (
            "You're a friendly cafe staff member double-checking the order or reservation. "
            "Be conversational and natural - like you're just making sure you got everything right. "
            "Only mention the key details that matter (what they ordered, when they're coming, etc.). "
            "Don't repeat obvious information. Sound like a real person, not a robot reading a checklist."
        )

    async def on_enter(self):
        """Present key information for confirmation in a natural way"""
        # Create a natural summary focusing on key details
        if hasattr(self.userdata, 'current_order') and self.userdata.current_order:
            # For orders - focus on items and pickup details
            order_summary = self._create_natural_order_summary()
            await self.session.generate_reply(
                instructions=f"Casually confirm the order details: {order_summary}. "
                "Sound natural and friendly, like you're just double-checking you got their order right.",
            )
        elif hasattr(self.userdata, 'reservation_date') and self.userdata.reservation_date:
            # For reservations - focus on time and party size
            reservation_summary = self._create_natural_reservation_summary()
            await self.session.generate_reply(
                instructions=f"Casually confirm the reservation: {reservation_summary}. "
                "Sound warm and welcoming, like you're looking forward to seeing them.",
            )
        else:
            await self.session.generate_reply(
                instructions="Something seems to be missing. Let me help you complete your order or reservation.",
            )

    def _create_natural_order_summary(self) -> str:
        """Create a natural summary of the order focusing on key details"""
        items = []
        if hasattr(self.userdata, 'current_order') and self.userdata.current_order:
            for item in self.userdata.current_order:
                qty = item.get('quantity', 1)
                name = item.get('item', '')
                if qty > 1:
                    items.append(f"{qty} {name}")
                else:
                    items.append(name)
        
        order_text = ", ".join(items) if items else "your order"
        
        # Add name if we have it
        name_part = ""
        if hasattr(self.userdata, 'customer_name') and self.userdata.customer_name:
            name_part = f" for {self.userdata.customer_name}"
        
        return f"{order_text}{name_part}"

    def _create_natural_reservation_summary(self) -> str:
        """Create a natural summary of the reservation focusing on key details"""
        parts = []
        
        if hasattr(self.userdata, 'reservation_date') and self.userdata.reservation_date:
            parts.append(f"on {self.userdata.reservation_date}")
        
        if hasattr(self.userdata, 'reservation_time') and self.userdata.reservation_time:
            parts.append(f"at {self.userdata.reservation_time}")
        
        if hasattr(self.userdata, 'party_size') and self.userdata.party_size:
            people = "person" if self.userdata.party_size == 1 else "people"
            parts.append(f"for {self.userdata.party_size} {people}")
        
        if hasattr(self.userdata, 'customer_name') and self.userdata.customer_name:
            parts.append(f"under {self.userdata.customer_name}")
        
        return "table " + " ".join(parts) if parts else "your reservation"

    @function_tool()
    async def confirm_order(self, context: RunContext[UserData]):
        """Confirm and save the order to Firebase"""
        try:
            if not (context.userdata.customer_name and context.userdata.customer_phone and 
                    hasattr(context.userdata, 'current_order') and context.userdata.current_order):
                return "I just need to get your name and phone number to complete this order."
            
            from app.models.restaurant import CustomerOrder, OrderItem
            from datetime import datetime
            import uuid
            
            # Convert current_order items to OrderItem objects
            order_items = []
            for item_data in context.userdata.current_order:
                order_item = OrderItem(
                    menu_item_id=item_data.get('item', ''),
                    quantity=item_data.get('quantity', 1),
                    unit_price=0.0,  # You'll need to look up the actual price
                    modifications=item_data.get('modifications', [])
                )
                order_items.append(order_item)
            
            # Create CustomerOrder object
            order = CustomerOrder(
                id=str(uuid.uuid4()),
                customer_phone=context.userdata.customer_phone,
                customer_name=context.userdata.customer_name,
                items=order_items,
                order_time=datetime.now(),
                status='pending',
                payment_method=getattr(context.userdata, 'payment_method', 'cash'),
                call_id=getattr(context.userdata, 'call_id', ''),
                agent_id=getattr(context.userdata, 'agent_id', ''),
                special_instructions=getattr(context.userdata, 'special_instructions', '')
            )
            
            await self.firebase.create_order(order)
            return "Perfect! Your order is all set. We'll have it ready for you soon!"
            
        except Exception as e:
            logger.error(f"Failed to save order: {e}")
            return "Oops, something went wrong on our end. Let me try that again for you."

    @function_tool()
    async def confirm_reservation(self, context: RunContext[UserData]):
        """Confirm and save the reservation to Firebase"""
        try:
            if not (context.userdata.customer_name and context.userdata.customer_phone and 
                    hasattr(context.userdata, 'reservation_date') and context.userdata.reservation_date and
                    hasattr(context.userdata, 'reservation_time') and context.userdata.reservation_time and
                    hasattr(context.userdata, 'party_size') and context.userdata.party_size > 0):
                return "I just need a few more details to get your table reserved."
            
            await self.firebase.save_reservation(context.userdata)
            return "Great! Your table is reserved. We're looking forward to seeing you!"
            
        except Exception as e:
            logger.error(f"Failed to save reservation: {e}")
            return "Oops, something went wrong on our end. Let me try that again for you."

    @function_tool()
    async def request_correction(self, context: RunContext[UserData], field: str, new_value: str):
        """Allow customer to correct specific information"""
        field_mapping = {
            'name': 'customer_name',
            'phone': 'customer_phone', 
            'email': 'customer_email',
            'date': 'reservation_date',
            'time': 'reservation_time',
            'party_size': 'party_size'
        }
        
        if field in field_mapping:
            attr_name = field_mapping[field]
            if field == 'party_size':
                setattr(context.userdata, attr_name, int(new_value))
            else:
                setattr(context.userdata, attr_name, new_value)
            return f"Got it, changed to {new_value}. Does everything look right now?"
        
        return "Just let me know what you'd like to change - your name, phone, date, time, or party size."

    @function_tool()
    async def cancel_request(self) -> str:
        """Cancel the current request"""
        return "No problem! What else can I help you with?"
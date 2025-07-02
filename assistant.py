

import asyncio
import logging
from typing import Dict
from manager import FirebaseManager

from livekit.agents import Agent, JobContext, WorkerOptions, cli, llm
from livekit.plugins import openai, silero, deepgram
from livekit import rtc

logger = logging.getLogger(__name__)

class VoiceAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice AI assistant.")

class FirebaseRestaurantAssistant:
    """Restaurant voice assistant with Firebase integration"""
    
    def __init__(self, firebase_credentials_path: str):
        self.firebase = FirebaseManager(firebase_credentials_path)
        self.current_orders = {}  # Call ID -> OrderData
        self.menu_cache = {}  # Cache menu for faster access
        
        # Load menu into cache
        asyncio.create_task(self._load_menu_cache())
    
    async def _load_menu_cache(self):
        """Load menu items into memory cache"""
        try:
            menu_items = await self.firebase.get_menu_items()
            self.menu_cache = {item.id: item for item in menu_items}
            logger.info(f"Loaded {len(menu_items)} menu items into cache")
        except Exception as e:
            logger.error(f"Error loading menu cache: {e}")
    
    def create_voice_assistant(self, call_context: Dict = None) -> VoiceAssistant:
        """Create voice assistant with Firebase-powered context"""
        
        # Generate dynamic system prompt with current menu
        system_prompt = self._generate_system_prompt(call_context)
        
        # Configure LLM
        llm_instance = openai.LLM(
            model="gpt-4",
            temperature=0.7,
            max_tokens=200,
        )
        
        # Configure STT optimized for restaurant environment
        stt = deepgram.STT(
            model="nova-2-phonecall",
            language="en-US",
            smart_format=True,
            punctuate=True,
            diarize=False,  # Single speaker expected
            keywords=["pizza", "pasta", "salad", "appetizer", "dessert", "order", "reservation"]
        )
        
        # Configure TTS
        tts = openai.TTS(
            voice="nova",
            speed=1.0,
        )
        
        # Create assistant
        assistant = VoiceAssistant(
            vad=silero.VAD.load(),
            stt=stt,
            llm=llm_instance,
            tts=tts,
            chat_ctx=llm.ChatContext(
                messages=[
                    llm.ChatMessage(
                        role="system",
                        content=system_prompt
                    )
                ]
            ),
        )
        
        return assistant
    
    def _generate_system_prompt(self, call_context: Dict = None) -> str:
        """Generate dynamic system prompt with current menu and customer context"""
        
        # Get available menu items
        available_items = [item for item in self.menu_cache.values() if item.available]
        
        # Organize by category
        menu_by_category = {}
        for item in available_items:
            if item.category not in menu_by_category:
                menu_by_category[item.category] = []
            menu_by_category[item.category].append(item)
        
        # Build menu text
        menu_text = "CURRENT MENU:\n"
        for category, items in menu_by_category.items():
            menu_text += f"\n{category.upper()}:\n"
            for item in items:
                allergen_info = f" (Contains: {', '.join(item.allergens)})" if item.allergens else ""
                menu_text += f"- {item.name}: ${item.price} - {item.description}{allergen_info}\n"
        
        # Add customer context if available
        customer_context = ""
        if call_context and call_context.get("customer_phone"):
            # This would be populated when we recognize the customer
            customer_context = f"\nCUSTOMER CONTEXT:\n{call_context.get('customer_history', '')}"
        
        return f"""
        You are a friendly voice assistant for Bella's Italian Kitchen. You help customers place orders over the phone.
        
        CORE BEHAVIORS:
        1. Greet customers warmly and ask how you can help
        2. Help customers navigate the menu and make selections
        3. Ask about quantities, modifications, and special requests
        4. Confirm orders clearly before finalizing
        5. Collect customer information (name and phone number)
        6. Provide estimated pickup/delivery times
        7. Handle dietary restrictions and allergen concerns
        
        {menu_text}
        
        {customer_context}
        
        IMPORTANT GUIDELINES:
        - Always confirm allergen information when customers ask
        - Suggest popular items or daily specials when appropriate
        - Be patient with elderly customers or those who need extra time
        - If an item is unavailable, suggest similar alternatives
        - Keep responses conversational and natural, not robotic
        - Use the available functions to search menu, add items, and access customer history
        
        Start each conversation with: "Hello! Thank you for calling Bella's Italian Kitchen. How can I help you today?"
        """
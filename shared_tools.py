# shared_tools.py - Shared function tools for all restaurant agents
import logging
import re
from typing import Annotated
from livekit.agents import function_tool, RunContext
from pydantic import Field
from app.models.restaurant import UserData

logger = logging.getLogger(__name__)

@function_tool()
async def update_customer_name(
    name: Annotated[str, Field(description="Customer's full name")],
    context: RunContext[UserData],
) -> str:
    """Update customer name in session data"""
    context.userdata.customer_name = name.strip().title()
    return f"Got it! I have your name as {context.userdata.customer_name}"

@function_tool()
async def update_customer_phone(
    phone: Annotated[str, Field(description="Customer's phone number")],
    context: RunContext[UserData],
) -> str:
    """Update customer phone number and fetch their history from Firebase"""
    # Clean phone number
    clean_phone = ''.join(filter(str.isdigit, phone))
    if len(clean_phone) == 10:
        clean_phone = f"+1{clean_phone}"
    elif len(clean_phone) == 11 and clean_phone.startswith('1'):
        clean_phone = f"+{clean_phone}"
    
    context.userdata.customer_phone = clean_phone
    
    # Get Firebase manager from the current agent
    if hasattr(context.session.current_agent, 'firebase'):
        firebase_manager = context.session.current_agent.firebase
        try:
            # Fetch customer history from Firebase
            customer_data = await firebase_manager.get_customer_data(clean_phone)
            
            if customer_data:
                # Update userdata with customer history
                context.userdata.customer_preferences = customer_data.get('preferences', {})
                context.userdata.loyalty_points = customer_data.get('loyalty_points', 0)
                context.userdata.order_history = customer_data.get('recent_orders', [])
                
                # Get customer name if we don't have it
                if not context.userdata.customer_name and customer_data.get('name'):
                    context.userdata.customer_name = customer_data.get('name')
                
                welcome_msg = f"Welcome back, {customer_data.get('name', 'valued customer')}!"
                if context.userdata.loyalty_points > 0:
                    welcome_msg += f" I see you have {context.userdata.loyalty_points} loyalty points."
                if context.userdata.order_history:
                    welcome_msg += f" Your last order was on {context.userdata.order_history[0].get('order_time', 'recently')}."
                
                return welcome_msg
            else:
                return f"Phone number updated to {clean_phone}. Welcome to our restaurant!"
                
        except Exception as e:
            logger.error(f"Error fetching customer data: {e}")
            return f"Phone number updated to {clean_phone}."
    else:
        return f"Phone number updated to {clean_phone}."

@function_tool()
async def update_customer_email(
    email: Annotated[str, Field(description="Customer's email address")],
    context: RunContext[UserData],
) -> str:
    """Update customer email address"""
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email.strip()):
        context.userdata.customer_email = email.strip().lower()
        return f"Email updated to {context.userdata.customer_email}"
    else:
        return "That doesn't look like a valid email address. Could you try again?"

@function_tool()
async def add_special_instructions(
    instructions: Annotated[str, Field(description="Special instructions for the order or reservation")],
    context: RunContext[UserData],
) -> str:
    """Add special instructions to the current request"""
    context.userdata.special_instructions = instructions
    return f"Added special instructions: {instructions}"

@function_tool()
async def get_customer_summary(
    context: RunContext[UserData],
) -> str:
    """Get a summary of the current customer session"""
    return context.userdata.summarize()

@function_tool()
async def check_loyalty_status(
    context: RunContext[UserData],
) -> str:
    """Check customer's loyalty points and status"""
    if context.userdata.loyalty_points > 0:
        return f"You have {context.userdata.loyalty_points} loyalty points available!"
    else:
        return "You don't have any loyalty points yet, but you'll start earning them with your next order!"
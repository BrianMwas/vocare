

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid
from livekit.agents import Agent


@dataclass
class MenuItem:
    """Restaurant menu item with Firebase document structure"""
    id: str
    name: str
    price: float
    description: str
    category: str
    available: bool = True
    prep_time_minutes: int = 15
    allergens: List[str] = None
    image_url: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if self.allergens is None:
            self.allergens = []
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to Firebase-compatible dictionary"""
        data = asdict(self)
        data['created_at'] = self.created_at
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MenuItem':
        """Create MenuItem from Firebase document"""
        return cls(**data)
    
    

@dataclass
class OrderItem:
    """Individual item in an order"""
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: float
    modifications: List[str] = None
    
    def __post_init__(self):
        if self.modifications is None:
            self.modifications = []
    
    @property
    def total_price(self) -> float:
        return self.unit_price * self.quantity
    

@dataclass
class CustomerOrder:
    """Complete customer order with Firebase integration"""
    id: str
    customer_phone: str
    customer_name: str
    items: List[OrderItem]
    order_time: datetime
    status: str = "pending"  # pending, confirmed, preparing, ready, completed, cancelled
    estimated_ready_time: datetime = None
    total_amount: float = 0.0
    payment_method: str = "cash"
    special_instructions: str = ""
    call_id: str = ""
    agent_id: str = ""
    
    def __post_init__(self):
        if self.estimated_ready_time is None:
            # Calculate estimated time based on items
            max_prep_time = max([20, len(self.items) * 5])  # Minimum 20 minutes
            self.estimated_ready_time = self.order_time + timedelta(minutes=max_prep_time)
        
        # Calculate total
        self.total_amount = sum(item.total_price for item in self.items)
    
    def to_dict(self) -> Dict:
        """Convert to Firebase-compatible dictionary"""
        return {
            'id': self.id,
            'customer_phone': self.customer_phone,
            'customer_name': self.customer_name,
            'items': [asdict(item) for item in self.items],
            'order_time': self.order_time,
            'status': self.status,
            'estimated_ready_time': self.estimated_ready_time,
            'total_amount': self.total_amount,
            'payment_method': self.payment_method,
            'special_instructions': self.special_instructions,
            'call_id': self.call_id,
            'agent_id': self.agent_id
        }
 
 
@dataclass
class CallLog:
    """Call analytics and logging"""
    id: str
    call_id: str
    caller_number: str
    start_time: datetime
    end_time: datetime = None
    duration_seconds: int = 0
    call_type: str = "general"  # order, reservation, complaint, inquiry
    order_id: str = ""
    agent_response_time_ms: int = 0
    customer_satisfaction: Optional[int] = None  # 1-5 rating
    transcript: str = ""
    resolution_status: str = "completed"  # completed, abandoned, transferred   
    
    

@dataclass
class UserData:
    """Comprehensive user session data"""
    # Customer information
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    
    # Order management
    current_order: List[Dict] = field(default_factory=list)
    order_total: float = 0.0
    special_instructions: str = ""
    
    # Reservation management
    reservation_date: str = ""
    reservation_time: str = ""
    party_size: int = 0
    
    # Payment information
    payment_method: str = "cash"  # cash, card, online
    credit_card_number: str = ""
    credit_card_expiry: str = ""
    credit_card_cvv: str = ""
    
    # Call context
    call_id: str = ""
    caller_number: str = ""
    call_start_time: datetime = field(default_factory=datetime.now)
    intent: str = ""  # order, reservation, inquiry, complaint
    
    # Agent management
    prev_agent: Optional[Agent] = None
    agents: Dict[str, Agent] = field(default_factory=dict)
    
    # Customer history (from Firebase)
    order_history: List[Dict] = field(default_factory=list)
    customer_preferences: Dict = field(default_factory=dict)
    loyalty_points: int = 0
    
    # Session state
    authenticated: bool = False
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def summarize(self) -> str:
        """Generate summary for agent context"""
        summary_parts = []
        
        if self.customer_name:
            summary_parts.append(f"Customer: {self.customer_name}")
        if self.customer_phone:
            summary_parts.append(f"Phone: {self.customer_phone}")
        if self.current_order:
            summary_parts.append(f"Current order: {len(self.current_order)} items, ${self.order_total:.2f}")
        if self.reservation_date and self.reservation_time:
            summary_parts.append(f"Reservation: {self.reservation_date} at {self.reservation_time} for {self.party_size}")
        if self.order_history:
            summary_parts.append(f"Previous orders: {len(self.order_history)}")
        if self.loyalty_points > 0:
            summary_parts.append(f"Loyalty points: {self.loyalty_points}")
        
        return "; ".join(summary_parts) if summary_parts else "New customer, no prior data"    
    


from datetime import datetime
import logging
from typing import Dict, List, Optional
import uuid
import asyncio

from firebase_admin import credentials, firestore
import firebase_admin
from google.cloud.firestore_v1.base_query import FieldFilter

from app.models.restaurant import CustomerOrder, MenuItem, UserData

# LOGGER = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

class FirebaseManager:
    """Handles all Firebase operations for the restaurant"""
    
    def __init__(self, credentials_path: str):
        """Initialize Firebase Admin SDK"""
        try:
            # Initialize Firebase Admin
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
            
            # Get Firestore client
            self.db = firestore.client()
            
            # Collection references
            self.menu_collection = self.db.collection('menu_items')
            self.orders_collection = self.db.collection('orders')
            self.customers_collection = self.db.collection('customers')
            self.call_logs_collection = self.db.collection('call_logs')
            self.analytics_collection = self.db.collection('analytics')
            
            # In-memory menu cache for faster access
            self.menu_items = {}
            
            logger.info("Firebase initialized successfully")
            
            # Load menu items into memory asynchronously
            self._load_menu()
            
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            raise

    def _load_menu(self):
        """Load menu items into memory for faster access"""
        try:
            docs = self.menu_collection.where('available', '==', True).stream()
            self.menu_items = {doc.id: doc.to_dict() for doc in docs}
            logger.info(f"Loaded {len(self.menu_items)} menu items into memory")
        except Exception as e:
            logger.error(f"Error loading menu: {e}")

    def get_menu_text(self) -> str:
        """Get formatted menu text for agent instructions"""
        if not self.menu_items:
            return "Menu currently unavailable"
        
        menu_by_category = {}
        for item in self.menu_items.values():
            category = item.get('category', 'other')
            if category not in menu_by_category:
                menu_by_category[category] = []
            menu_by_category[category].append(item)
        
        menu_text = ""
        for category, items in menu_by_category.items():
            menu_text += f"\n{category.upper()}:\n"
            for item in items:
                menu_text += f"- {item['name']}: ${item['price']} - {item['description']}\n"
        
        return menu_text
    
    
    async def get_menu_items(self, category: Optional[str] = None, available_only: bool = True) -> List[MenuItem]:
        """Get menu items, optionally filtered by category"""
        try:
            query = self.menu_collection
            
            if available_only:
                query = query.where(filter=FieldFilter("available", "==", True))
            
            if category:
                query = query.where(filter=FieldFilter("category", "==", category))
            
            docs = query.stream()
            
            items = []
            for doc_snapshot in docs:
                if doc_snapshot.exists:
                    data = doc_snapshot.to_dict()
                    data['id'] = doc_snapshot.id
                    item = MenuItem.from_dict(data) 
                    items.append(item)
            
            logger.info(f"Retrieved {len(items)} menu items")
            return items
            
        except Exception as e:
            logger.error(f"Error getting menu items: {e}")
            return []
        
    
    async def search_menu_items(self, search_term: str) -> List[MenuItem]:
        """Search menu items by name or description"""
        try:
            # Firebase doesn't have full-text search, so we'll get all items and filter
            all_items = self.get_menu_items()
            
            search_term = search_term.lower()
            matching_items = []
            
            for item in all_items:
                if (search_term in item.name.lower() or 
                    search_term in item.description.lower() or
                    any(search_term in allergen.lower() for allergen in item.allergens)):
                    matching_items.append(item)
            
            logger.info(f"Found {len(matching_items)} items matching '{search_term}'")
            return matching_items
            
        except Exception as e:
            logger.error(f"Error searching menu items: {e}")
            return []
        
    async def update_item_availability(self, item_id: str, available: bool):
        """Update menu item availability in real-time"""
        try:
            self.menu_collection.document(item_id).update({
                'available': available,
                'updated_at': datetime.now()
            })
            logger.info(f"Updated availability for item {item_id}: {available}")
            
        except Exception as e:
            logger.error(f"Error updating item availability: {e}")
            
    
    # === ORDER OPERATIONS ===
    
    async def create_order(self, order: CustomerOrder) -> bool:
        """Create new order in Firebase"""
        try:
            order_ref = self.orders_collection.document(order.id)
            order_ref.set(order.to_dict())
            
            # Update customer info
            self._update_customer_info(order.customer_phone, order.customer_name)
            
            # Update analytics
            self._update_order_analytics(order)
            
            logger.info(f"Created order {order.id} for ${order.total_amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return False
    
    def update_order_status(self, order_id: str, status: str):
        """Update order status with timestamp"""
        try:
            self.orders_collection.document(order_id).update({
                'status': status,
                'status_updated_at': datetime.now()
            })
            
            logger.info(f"Updated order {order_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            
    async def get_customer_order_history(self, phone_number: str, limit: int = 10) -> List[Dict]:
        """Get customer's recent order history"""
        try:
            query = (self.orders_collection
                    .where(filter=FieldFilter("customer_phone", "==", phone_number))
                    .order_by("order_time", direction="DESCENDING")
                    .limit(limit))
            
            docs = query.stream()
            
            # Output from the stream generator
            orders = [doc.to_dict() for doc in docs]
            
            logger.info(f"Retrieved {len(orders)} orders for {phone_number}")
            return orders
            
        except Exception as e:
            logger.error(f"Error getting customer order history: {e}")
            return []

    async def get_customer_data(self, phone_number: str) -> Dict:
        """Get comprehensive customer data including history and preferences"""
        try:
            # Get customer document
            customer_doc = self.customers_collection.document(phone_number).get()
            
            if customer_doc.exists:
                customer_data = customer_doc.to_dict()
                
                # Get recent order history
                order_history = await self.get_customer_order_history(phone_number, limit=5)
                customer_data['recent_orders'] = order_history
                
                # Get customer preferences if available
                preferences = await self.get_customer_preferences(phone_number)
                customer_data['preferences'] = preferences
                
                logger.info(f"Found existing customer data for {phone_number}")
                return customer_data
            else:
                logger.info(f"No existing customer data found for {phone_number}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting customer data: {e}")
            return {}
        

    # === CUSTOMER OPERATIONS ===
    def _update_customer_info(self, phone: str, name: str):
        """Update or create customer record"""
        try:
            customer_ref = self.customers_collection.document(phone)
            
            # Check if customer exists
            customer_doc = customer_ref.get()
            
            if customer_doc.exists:
                # Update existing customer
                customer_ref.update({
                    'name': name,
                    'last_order_time': datetime.now(),
                    'total_orders': firestore.Increment(1)
                })
            else:
                # Create new customer
                customer_ref.set({
                    'phone': phone,
                    'name': name,
                    'first_order_time': datetime.now(),
                    'last_order_time': datetime.now(),
                    'total_orders': 1,
                    'preferred_items': [],
                    'dietary_restrictions': []
                })
            
        except Exception as e:
            logger.error(f"Error updating customer info: {e}")
    
    async def save_reservation(self, userdata: UserData) -> bool:
        """Save reservation to Firebase"""
        try:
            reservation_data = {
                'id': str(uuid.uuid4()),
                'customer_name': userdata.customer_name,
                'customer_phone': userdata.customer_phone,
                'reservation_date': userdata.reservation_date,
                'reservation_time': userdata.reservation_time,
                'party_size': userdata.party_size,
                'created_at': datetime.now(),
                'status': 'confirmed',
                'call_id': userdata.call_id
            }
            
            await self.db.collection('reservations').add(reservation_data)
            logger.info(f"Saved reservation for {userdata.customer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving reservation: {e}")
            return False
        
    async def get_customer_preferences(self, phone: str) -> Dict:
        """Get customer preferences and history"""
        try:
            customer_doc = self.customers_collection.document(phone).get()
            
            if customer_doc.exists:
                return customer_doc.to_dict()
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting customer preferences: {e}")
            return {}
        
    
    async def _update_order_analytics(self, order: CustomerOrder):
        """Update daily analytics with new order"""
        try:
            today = datetime.now().date()
            analytics_ref = self.analytics_collection.document(today.isoformat())
            

            analytics_ref.set({
                'date': today,
                'total_orders': firestore.Increment(1),
                'total_revenue': firestore.Increment(order.total_amount),
                'updated_at': datetime.now()
            }, merge=True)
            
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
    
    async def get_daily_stats(self, date: datetime = None) -> Dict:
        """Get daily restaurant statistics"""
        try:
            if date is None:
                date = datetime.now()
            
            analytics_doc = self.analytics_collection.document(date.isoformat()).get()
            
            if analytics_doc.exists:
                return analytics_doc.to_dict()
            else:
                return {
                    'date': date,
                    'total_orders': 0,
                    'total_revenue': 0.0,
                    'average_order_value': 0.0
                }
                
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {}
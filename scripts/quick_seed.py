#!/usr/bin/env python3
"""
Quick Menu Seeding Script - Simple version for Docker/production
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from manager import FirebaseManager

# Simple menu data for quick seeding
QUICK_MENU = [
    {
        "name": "Margherita Pizza",
        "description": "Fresh mozzarella, tomato sauce, and basil",
        "price": 18.99,
        "category": "mains",
        "available": True,
        "prep_time_minutes": 12,
        "allergens": ["gluten", "dairy"],
        "created_at": datetime.now()
    },
    {
        "name": "Caesar Salad",
        "description": "Romaine lettuce, croutons, parmesan, Caesar dressing",
        "price": 12.99,
        "category": "salads",
        "available": True,
        "prep_time_minutes": 8,
        "allergens": ["gluten", "dairy", "eggs"],
        "created_at": datetime.now()
    },
    {
        "name": "Grilled Chicken",
        "description": "Herb-marinated chicken breast with vegetables",
        "price": 24.99,
        "category": "mains",
        "available": True,
        "prep_time_minutes": 20,
        "allergens": [],
        "created_at": datetime.now()
    },
    {
        "name": "Chocolate Cake",
        "description": "Rich chocolate cake with vanilla ice cream",
        "price": 8.99,
        "category": "desserts",
        "available": True,
        "prep_time_minutes": 5,
        "allergens": ["gluten", "dairy", "eggs"],
        "created_at": datetime.now()
    },
    {
        "name": "Coffee",
        "description": "Freshly brewed house blend coffee",
        "price": 3.99,
        "category": "beverages",
        "available": True,
        "prep_time_minutes": 2,
        "allergens": [],
        "created_at": datetime.now()
    }
]

async def quick_seed():
    """Quick seed with basic menu items"""
    try:
        firebase = FirebaseManager(os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service.json"))
        
        print("Adding basic menu items...")
        for item in QUICK_MENU:
            doc_ref = firebase.menu_collection.add(item)
            doc_id = doc_ref[1].id  # doc_ref is a tuple (timestamp, DocumentReference)
            print(f"✅ Added {item['name']} with ID: {doc_id}")
        
        # Reload menu
        await firebase._load_menu()
        print(f"\n🎉 Successfully added {len(QUICK_MENU)} menu items!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(quick_seed())
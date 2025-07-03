#!/usr/bin/env python3
"""
Menu Management Script - Add, update, or remove menu items
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import argparse
from datetime import datetime
from manager import FirebaseManager

class MenuManager:
    def __init__(self):
        self.firebase = FirebaseManager(os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service.json"))
    
    async def list_items(self):
        """List all menu items"""
        try:
            docs = self.firebase.menu_collection.stream()
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            
            if not items:
                print("No menu items found.")
                return
            
            print(f"\n📋 Menu Items ({len(items)} total):")
            print("-" * 60)
            
            for item in sorted(items, key=lambda x: x.get('category', '')):
                status = "✅" if item.get('available', True) else "❌"
                print(f"{status} {item['name']} - ${item['price']} ({item.get('category', 'uncategorized')})")
                
        except Exception as e:
            print(f"❌ Error listing items: {e}")
    
    async def add_item(self, name: str, price: float, category: str, description: str = ""):
        """Add a new menu item"""
        try:
            item_data = {
                "name": name,
                "description": description,
                "price": price,
                "category": category,
                "available": True,
                "prep_time_minutes": 15,
                "allergens": [],
                "created_at": datetime.now()
            }
            
            doc_ref = await self.firebase.menu_collection.add(item_data)
            print(f"✅ Added '{name}' with ID: {doc_ref.id}")
            
            # Reload menu cache
            await self.firebase._load_menu()
            
        except Exception as e:
            print(f"❌ Error adding item: {e}")
    
    async def remove_item(self, item_name: str):
        """Remove a menu item by name"""
        try:
            docs = self.firebase.menu_collection.where('name', '==', item_name).stream()
            found = False
            
            for doc in docs:
                await doc.reference.delete()
                print(f"✅ Removed '{item_name}'")
                found = True
            
            if not found:
                print(f"❌ Item '{item_name}' not found")
            else:
                # Reload menu cache
                await self.firebase._load_menu()
                
        except Exception as e:
            print(f"❌ Error removing item: {e}")
    
    async def toggle_availability(self, item_name: str):
        """Toggle availability of a menu item"""
        try:
            docs = self.firebase.menu_collection.where('name', '==', item_name).stream()
            found = False
            
            for doc in docs:
                data = doc.to_dict()
                new_status = not data.get('available', True)
                
                await doc.reference.update({'available': new_status})
                status_text = "available" if new_status else "unavailable"
                print(f"✅ '{item_name}' is now {status_text}")
                found = True
            
            if not found:
                print(f"❌ Item '{item_name}' not found")
            else:
                # Reload menu cache
                await self.firebase._load_menu()
                
        except Exception as e:
            print(f"❌ Error toggling availability: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Restaurant Menu Manager")
    parser.add_argument('action', choices=['list', 'add', 'remove', 'toggle'], 
                       help='Action to perform')
    parser.add_argument('--name', help='Menu item name')
    parser.add_argument('--price', type=float, help='Item price')
    parser.add_argument('--category', help='Item category')
    parser.add_argument('--description', help='Item description')
    
    args = parser.parse_args()
    
    manager = MenuManager()
    
    if args.action == 'list':
        await manager.list_items()
    
    elif args.action == 'add':
        if not all([args.name, args.price, args.category]):
            print("❌ Error: --name, --price, and --category are required for adding items")
            return
        await manager.add_item(args.name, args.price, args.category, args.description or "")
    
    elif args.action == 'remove':
        if not args.name:
            print("❌ Error: --name is required for removing items")
            return
        await manager.remove_item(args.name)
    
    elif args.action == 'toggle':
        if not args.name:
            print("❌ Error: --name is required for toggling availability")
            return
        await manager.toggle_availability(args.name)

if __name__ == "__main__":
    asyncio.run(main())
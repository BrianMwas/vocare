#!/usr/bin/env python3
"""
Menu Seeding Script for Restaurant Firebase Database
Populates the menu_items collection with comprehensive menu data.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from manager import FirebaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MenuSeeder:
    def __init__(self, firebase_manager: FirebaseManager):
        self.firebase = firebase_manager
        
    def seed_menu_items(self, clear_existing: bool = False):
        """Seed the database with menu items"""
        
        if clear_existing:
            self.clear_existing_menu()
        
        menu_data = self.get_menu_data()
        
        logger.info(f"Seeding {len(menu_data)} menu items...")
        
        for item in menu_data:
            try:
                # Add to Firebase (using synchronous method since Firestore client is sync)
                doc_ref = self.firebase.menu_collection.add(item)
                doc_id = doc_ref[1].id  # doc_ref is a tuple (timestamp, DocumentReference)
                logger.info(f"Added {item['name']} with ID: {doc_id}")
                
            except Exception as e:
                logger.error(f"Error adding {item['name']}: {e}")
        
        logger.info("Menu seeding completed!")
        
        # Note: Menu will be loaded when firebase manager is used next time
        
    def clear_existing_menu(self):
        """Clear existing menu items (use with caution!)"""
        logger.warning("Clearing existing menu items...")
        
        docs = self.firebase.menu_collection.stream()
        for doc in docs:
            doc.reference.delete()
            logger.info(f"Deleted menu item: {doc.id}")
    
    def get_menu_data(self) -> List[Dict]:
        """Define comprehensive menu data for a modern restaurant"""
        menu_items = [
            # === APPETIZERS ===
            {
                "name": "Truffle Arancini",
                "description": "Crispy risotto balls stuffed with mozzarella and truffle oil, served with marinara sauce",
                "price": 14.99,
                "category": "appetizers",
                "available": True,
                "prep_time_minutes": 12,
                "allergens": ["gluten", "dairy"],
                "image_url": "https://images.example.com/truffle-arancini.jpg",
                "created_at": datetime.now(),
                "popularity_score": 85,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": False
            },
            {
                "name": "Korean BBQ Wings",
                "description": "Crispy chicken wings glazed with gochujang and sesame, topped with scallions",
                "price": 16.99,
                "category": "appetizers",
                "available": True,
                "prep_time_minutes": 15,
                "allergens": ["soy", "sesame"],
                "image_url": "https://images.example.com/korean-wings.jpg",
                "created_at": datetime.now(),
                "popularity_score": 92,
                "spice_level": 2,
                "vegetarian": False,
                "vegan": False,
                "gluten_free": True
            },
            {
                "name": "Burrata Caprese",
                "description": "Fresh burrata cheese with heirloom tomatoes, basil, and aged balsamic reduction",
                "price": 18.99,
                "category": "appetizers",
                "available": True,
                "prep_time_minutes": 8,
                "allergens": ["dairy"],
                "image_url": "https://images.example.com/burrata-caprese.jpg",
                "created_at": datetime.now(),
                "popularity_score": 88,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": True
            },
            
            # === SOUPS & SALADS ===
            {
                "name": "Roasted Tomato Bisque",
                "description": "Creamy roasted tomato soup with fresh herbs and a swirl of cream",
                "price": 9.99,
                "category": "soups_salads",
                "available": True,
                "prep_time_minutes": 5,
                "allergens": ["dairy"],
                "image_url": "https://images.example.com/tomato-bisque.jpg",
                "created_at": datetime.now(),
                "popularity_score": 78,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": True
            },
            {
                "name": "Mediterranean Quinoa Bowl",
                "description": "Quinoa with roasted vegetables, feta, olives, and lemon-herb dressing",
                "price": 15.99,
                "category": "soups_salads",
                "available": True,
                "prep_time_minutes": 10,
                "allergens": ["dairy"],
                "image_url": "https://images.example.com/quinoa-bowl.jpg",
                "created_at": datetime.now(),
                "popularity_score": 82,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": True
            },
            {
                "name": "Caesar Salad",
                "description": "Crisp romaine, house-made croutons, parmesan, and our signature Caesar dressing",
                "price": 12.99,
                "category": "soups_salads",
                "available": True,
                "prep_time_minutes": 7,
                "allergens": ["gluten", "dairy", "eggs"],
                "image_url": "https://images.example.com/caesar-salad.jpg",
                "created_at": datetime.now(),
                "popularity_score": 75,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": False
            },
            
            # === MAIN COURSES ===
            {
                "name": "Grilled Salmon",
                "description": "Atlantic salmon with lemon-dill butter, roasted vegetables, and wild rice",
                "price": 28.99,
                "category": "mains",
                "available": True,
                "prep_time_minutes": 18,
                "allergens": ["fish", "dairy"],
                "image_url": "https://images.example.com/grilled-salmon.jpg",
                "created_at": datetime.now(),
                "popularity_score": 89,
                "spice_level": 0,
                "vegetarian": False,
                "vegan": False,
                "gluten_free": True
            },
            {
                "name": "Braised Short Ribs",
                "description": "Slow-braised beef short ribs with red wine reduction, mashed potatoes, and seasonal vegetables",
                "price": 32.99,
                "category": "mains",
                "available": True,
                "prep_time_minutes": 25,
                "allergens": ["dairy"],
                "image_url": "https://images.example.com/short-ribs.jpg",
                "created_at": datetime.now(),
                "popularity_score": 94,
                "spice_level": 0,
                "vegetarian": False,
                "vegan": False,
                "gluten_free": True
            },
            {
                "name": "Margherita Pizza",
                "description": "Classic pizza with fresh mozzarella, tomato sauce, and basil on wood-fired crust",
                "price": 18.99,
                "category": "mains",
                "available": True,
                "prep_time_minutes": 12,
                "allergens": ["gluten", "dairy"],
                "image_url": "https://images.example.com/margherita-pizza.jpg",
                "created_at": datetime.now(),
                "popularity_score": 86,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": False
            },
            {
                "name": "Mushroom Risotto",
                "description": "Creamy arborio rice with wild mushrooms, truffle oil, and parmesan",
                "price": 22.99,
                "category": "mains",
                "available": True,
                "prep_time_minutes": 20,
                "allergens": ["dairy"],
                "image_url": "https://images.example.com/mushroom-risotto.jpg",
                "created_at": datetime.now(),
                "popularity_score": 81,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": True
            },
            {
                "name": "Thai Green Curry",
                "description": "Coconut green curry with vegetables, jasmine rice, choice of chicken or tofu",
                "price": 19.99,
                "category": "mains",
                "available": True,
                "prep_time_minutes": 15,
                "allergens": ["coconut"],
                "image_url": "https://images.example.com/green-curry.jpg",
                "created_at": datetime.now(),
                "popularity_score": 87,
                "spice_level": 3,
                "vegetarian": True,  # Can be made vegetarian with tofu
                "vegan": True,  # Can be made vegan with tofu
                "gluten_free": True
            },
            
            # === PASTA ===
            {
                "name": "Spaghetti Carbonara",
                "description": "Fresh spaghetti with pancetta, egg yolk, parmesan, and black pepper",
                "price": 21.99,
                "category": "pasta",
                "available": True,
                "prep_time_minutes": 14,
                "allergens": ["gluten", "dairy", "eggs"],
                "image_url": "https://images.example.com/carbonara.jpg",
                "created_at": datetime.now(),
                "popularity_score": 90,
                "spice_level": 0,
                "vegetarian": False,
                "vegan": False,
                "gluten_free": False
            },
            {
                "name": "Lobster Ravioli",
                "description": "House-made ravioli stuffed with lobster and ricotta in lemon butter sauce",
                "price": 29.99,
                "category": "pasta",
                "available": True,
                "prep_time_minutes": 16,
                "allergens": ["gluten", "dairy", "shellfish", "eggs"],
                "image_url": "https://images.example.com/lobster-ravioli.jpg",
                "created_at": datetime.now(),
                "popularity_score": 93,
                "spice_level": 0,
                "vegetarian": False,
                "vegan": False,
                "gluten_free": False
            },
            
            # === DESSERTS ===
            {
                "name": "Chocolate Lava Cake",
                "description": "Warm chocolate cake with molten center, vanilla ice cream, and berry coulis",
                "price": 12.99,
                "category": "desserts",
                "available": True,
                "prep_time_minutes": 8,
                "allergens": ["gluten", "dairy", "eggs"],
                "image_url": "https://images.example.com/lava-cake.jpg",
                "created_at": datetime.now(),
                "popularity_score": 91,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": False
            },
            {
                "name": "Tiramisu",
                "description": "Classic Italian dessert with espresso-soaked ladyfingers and mascarpone",
                "price": 10.99,
                "category": "desserts",
                "available": True,
                "prep_time_minutes": 5,
                "allergens": ["gluten", "dairy", "eggs"],
                "image_url": "https://images.example.com/tiramisu.jpg",
                "created_at": datetime.now(),
                "popularity_score": 85,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": False
            },
            {
                "name": "Seasonal Fruit Tart",
                "description": "Pastry cream tart topped with fresh seasonal fruits and mint",
                "price": 9.99,
                "category": "desserts",
                "available": True,
                "prep_time_minutes": 5,
                "allergens": ["gluten", "dairy", "eggs"],
                "image_url": "https://images.example.com/fruit-tart.jpg",
                "created_at": datetime.now(),
                "popularity_score": 76,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": False,
                "gluten_free": False
            },
            
            # === BEVERAGES ===
            {
                "name": "Craft Coffee",
                "description": "Locally roasted single-origin coffee, served hot or iced",
                "price": 4.99,
                "category": "beverages",
                "available": True,
                "prep_time_minutes": 3,
                "allergens": [],
                "image_url": "https://images.example.com/craft-coffee.jpg",
                "created_at": datetime.now(),
                "popularity_score": 88,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": True,
                "gluten_free": True
            },
            {
                "name": "Fresh Squeezed Orange Juice",
                "description": "100% fresh Valencia oranges, squeezed to order",
                "price": 6.99,
                "category": "beverages",
                "available": True,
                "prep_time_minutes": 2,
                "allergens": [],
                "image_url": "https://images.example.com/orange-juice.jpg",
                "created_at": datetime.now(),
                "popularity_score": 82,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": True,
                "gluten_free": True
            },
            {
                "name": "House Wine Selection",
                "description": "Curated selection of red and white wines by the glass",
                "price": 8.99,
                "category": "beverages",
                "available": True,
                "prep_time_minutes": 2,
                "allergens": ["sulfites"],
                "image_url": "https://images.example.com/wine-glass.jpg",
                "created_at": datetime.now(),
                "popularity_score": 79,
                "spice_level": 0,
                "vegetarian": True,
                "vegan": True,  # Most wines are vegan
                "gluten_free": True
            },
            
            # === SPECIAL ITEMS (Limited Availability) ===
            {
                "name": "Chef's Special Tasting Menu",
                "description": "5-course tasting menu featuring seasonal ingredients (changes weekly)",
                "price": 75.00,
                "category": "specials",
                "available": False,  # Currently unavailable
                "prep_time_minutes": 45,
                "allergens": ["varies"],
                "image_url": "https://images.example.com/tasting-menu.jpg",
                "created_at": datetime.now(),
                "popularity_score": 95,
                "spice_level": 0,
                "vegetarian": False,
                "vegan": False,
                "gluten_free": False
            }
        ]
        
        return menu_items


def main():
    """Main function to run the seeding script"""
    import sys
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Restaurant Menu Seeding Script")
    parser.add_argument('--clear', action='store_true', help='Clear existing menu items first')
    parser.add_argument('--force', action='store_true', help='Force operation without confirmation')
    args = parser.parse_args()
    
    try:
        # Initialize Firebase Manager
        firebase_manager = FirebaseManager("service.json")
        
        # Create seeder
        seeder = MenuSeeder(firebase_manager)
        
        print("🍽️  Restaurant Menu Seeding Script")
        print("=" * 40)
        print("This will add menu items to your Firebase database.")
        
        # Determine if we should clear existing items
        clear_existing = args.clear
        
        if clear_existing and not args.force:
            # Check if running in interactive mode
            interactive = sys.stdin.isatty()
            
            if interactive:
                confirm = input("\n⚠️  This will DELETE all existing menu items. Are you sure? (y/N): ").lower().strip()
                if confirm != 'y':
                    print("❌ Seeding cancelled.")
                    return
            else:
                print("❌ Cannot clear items in non-interactive mode without --force flag")
                print("Use: python seed_menu.py --clear --force")
                return
        
        if not clear_existing:
            print("\n📝 Adding menu items (keeping existing ones)")
        else:
            print("\n🗑️  Will clear existing items and add new ones")
        
        # Run seeding
        seeder.seed_menu_items(clear_existing=clear_existing)
        
        # Display results
        print("\n✅ Menu seeding completed successfully!")
        print(f"📋 Menu preview:")
        menu_text = firebase_manager.get_menu_text()
        print(menu_text[:500] + "..." if len(menu_text) > 500 else menu_text)
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
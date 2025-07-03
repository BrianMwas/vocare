# Restaurant Assistant Makefile

.PHONY: help seed-menu quick-seed list-menu add-item remove-item setup clean

help:
	@echo "🍽️  Restaurant Assistant Commands"
	@echo "================================"
	@echo "Menu Management:"
	@echo "  seed-menu     - Seed database with comprehensive menu (interactive)"
	@echo "  quick-seed    - Add basic menu items quickly"
	@echo "  list-menu     - List all menu items"
	@echo "  add-item      - Add a new menu item (requires params)"
	@echo "  remove-item   - Remove a menu item (requires name)"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-seed   - Seed menu using Docker"
	@echo "  docker-up     - Start all services"
	@echo "  docker-down   - Stop all services"
	@echo ""
	@echo "Setup:"
	@echo "  setup         - Install dependencies"
	@echo "  clean         - Clean up temporary files"

# Menu seeding
seed-menu:
	@echo "🌱 Seeding comprehensive menu..."
	python seed_menu.py

seed-menu-clear:
	@echo "🗑️  Clearing and seeding comprehensive menu..."
	python seed_menu.py --clear

quick-seed:
	@echo "⚡ Quick seeding basic menu items..."
	python scripts/quick_seed.py

# Menu management
list-menu:
	@echo "📋 Listing menu items..."
	python scripts/menu_manager.py list

add-item:
	@echo "➕ Adding menu item..."
	@echo "Usage: make add-item NAME='Item Name' PRICE=12.99 CATEGORY=mains DESCRIPTION='Description'"
	@if [ -z "$(NAME)" ] || [ -z "$(PRICE)" ] || [ -z "$(CATEGORY)" ]; then \
		echo "❌ Error: NAME, PRICE, and CATEGORY are required"; \
		echo "Example: make add-item NAME='Pasta Alfredo' PRICE=18.99 CATEGORY=pasta DESCRIPTION='Creamy pasta dish'"; \
	else \
		python scripts/menu_manager.py add --name "$(NAME)" --price $(PRICE) --category $(CATEGORY) --description "$(DESCRIPTION)"; \
	fi

remove-item:
	@echo "🗑️  Removing menu item..."
	@if [ -z "$(NAME)" ]; then \
		echo "❌ Error: NAME is required"; \
		echo "Usage: make remove-item NAME='Item Name'"; \
	else \
		python scripts/menu_manager.py remove --name "$(NAME)"; \
	fi

toggle-item:
	@echo "🔄 Toggling item availability..."
	@if [ -z "$(NAME)" ]; then \
		echo "❌ Error: NAME is required"; \
		echo "Usage: make toggle-item NAME='Item Name'"; \
	else \
		python scripts/menu_manager.py toggle --name "$(NAME)"; \
	fi

# Docker commands
docker-seed:
	@echo "🐳 Seeding menu with Docker..."
	docker-compose --profile tools run --rm menu-seeder

docker-up:
	@echo "🚀 Starting restaurant assistant..."
	docker-compose up -d

docker-down:
	@echo "🛑 Stopping services..."
	docker-compose down

docker-logs:
	@echo "📋 Showing logs..."
	docker-compose logs -f backend

# Setup and maintenance
setup:
	@echo "🔧 Setting up development environment..."
	pip install -r requirements.txt
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Copy .env.example to .env and add your API keys"
	@echo "2. Add your Firebase service.json file"
	@echo "3. Run 'make quick-seed' to add basic menu items"
	@echo "4. Run 'python main.py' to start the assistant"

clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "✅ Cleanup complete!"

# Development helpers
dev-run:
	@echo "🔧 Running in development mode..."
	python main.py

test-menu:
	@echo "🧪 Testing menu loading..."
	python -c "import asyncio; from manager import FirebaseManager; fm = FirebaseManager('service.json'); print(fm.get_menu_text())"

# Example commands for reference
examples:
	@echo "📚 Example Commands:"
	@echo ""
	@echo "Add a new pizza:"
	@echo "  make add-item NAME='Pepperoni Pizza' PRICE=16.99 CATEGORY=mains DESCRIPTION='Classic pepperoni pizza'"
	@echo ""
	@echo "Remove an item:"
	@echo "  make remove-item NAME='Pepperoni Pizza'"
	@echo ""
	@echo "Toggle availability:"
	@echo "  make toggle-item NAME='Pepperoni Pizza'"
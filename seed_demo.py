#!/usr/bin/env python3
"""
Quick demo data seeder for testing the application
"""

from app import app, db
from models import User, Auction, Item, Partner, ItemPartner, ItemExpense, ItemSale, ItemStatus
from datetime import datetime, date, timedelta
from decimal import Decimal
import random

def create_demo_user():
    """Create a demo user for testing"""
    user = User()
    user.id = 'demo-user-123'
    user.email = 'demo@example.com'
    user.first_name = 'Demo'
    user.last_name = 'User'
    user.profile_image_url = None
    
    existing = User.query.filter_by(id=user.id).first()
    if existing:
        return existing
    
    db.session.add(user)
    db.session.commit()
    return user

def create_demo_data():
    """Create demo auction data"""
    with app.app_context():
        print("Creating demo data...")
        
        # Create demo user
        user = create_demo_user()
        
        # Create auctions
        auction1 = Auction()
        auction1.title = "Construction Equipment Auction"
        auction1.date = date.today() + timedelta(days=7)
        auction1.location = "Local Auction House"
        auction1.url = "https://example.com/auction1"
        auction1.notes = "Great selection of tools and equipment"
        
        auction2 = Auction()
        auction2.title = "Estate Sale - Farm Equipment"
        auction2.date = date.today() - timedelta(days=30)
        auction2.location = "Farm Location"
        auction2.url = "https://example.com/auction2"
        auction2.notes = "Vintage farm equipment and tools"
        
        db.session.add(auction1)
        db.session.add(auction2)
        db.session.commit()
        
        # Create partners
        partner1 = Partner()
        partner1.name = "John Smith"
        partner1.email = "john@example.com"
        
        partner2 = Partner()
        partner2.name = "Mike Johnson"
        partner2.email = "mike@example.com"
        
        db.session.add(partner1)
        db.session.add(partner2)
        db.session.commit()
        
        # Create items with different statuses
        items_data = [
            # Watchlist items
            {
                'title': 'DeWalt Power Tool Set',
                'auction_id': auction1.id,
                'lot_number': 'LOT-001',
                'description': 'Complete set of DeWalt power tools',
                'planned_max_bid': Decimal('150.00'),
                'target_resale_price': Decimal('300.00'),
                'status': ItemStatus.WATCH
            },
            {
                'title': 'Vintage Table Saw',
                'auction_id': auction1.id,
                'lot_number': 'LOT-015',
                'description': 'Vintage Craftsman table saw in good condition',
                'planned_max_bid': Decimal('200.00'),
                'target_resale_price': Decimal('450.00'),
                'status': ItemStatus.WATCH
            },
            # Won items (inventory)
            {
                'title': 'Lumber Bundle - Pine 2x4s',
                'auction_id': auction2.id,
                'lot_number': 'LOT-032',
                'description': 'Bundle of 50 pine 2x4s, 8ft length',
                'planned_max_bid': Decimal('100.00'),
                'target_resale_price': Decimal('250.00'),
                'status': ItemStatus.WON,
                'purchase_price': Decimal('85.00'),
                'refurb_cost': Decimal('10.00'),
                'multiple_pieces': True,
                'pieces_total': 50,
                'pieces_remaining': 35
            },
            {
                'title': 'Antique Drill Press',
                'auction_id': auction2.id,
                'lot_number': 'LOT-008',
                'description': 'Restored antique drill press',
                'planned_max_bid': Decimal('300.00'),
                'target_resale_price': Decimal('600.00'),
                'status': ItemStatus.WON,
                'purchase_price': Decimal('275.00'),
                'refurb_cost': Decimal('125.00')
            },
            # Sold items
            {
                'title': 'Welding Equipment Set',
                'auction_id': auction2.id,
                'lot_number': 'LOT-025',
                'description': 'Complete welding setup',
                'planned_max_bid': Decimal('400.00'),
                'target_resale_price': Decimal('800.00'),
                'status': ItemStatus.SOLD,
                'purchase_price': Decimal('380.00'),
                'refurb_cost': Decimal('50.00'),
                'sale_price': Decimal('750.00'),
                'sale_date': date.today() - timedelta(days=5),
                'sale_fees': Decimal('37.50'),
                'shipping_cost': Decimal('25.00'),
                'list_date': date.today() - timedelta(days=15),
                'list_channel': 'eBay'
            },
            {
                'title': 'Router and Accessories',
                'auction_id': auction2.id,
                'lot_number': 'LOT-012',
                'description': 'Router with complete bit set',
                'planned_max_bid': Decimal('120.00'),
                'target_resale_price': Decimal('220.00'),
                'status': ItemStatus.SOLD,
                'purchase_price': Decimal('95.00'),
                'refurb_cost': Decimal('15.00'),
                'sale_price': Decimal('210.00'),
                'sale_date': date.today() - timedelta(days=12),
                'sale_fees': Decimal('21.00'),
                'shipping_cost': Decimal('15.00'),
                'list_date': date.today() - timedelta(days=25),
                'list_channel': 'Facebook Marketplace'
            }
        ]
        
        items = []
        for item_data in items_data:
            item = Item()
            for key, value in item_data.items():
                setattr(item, key, value)
            db.session.add(item)
            items.append(item)
        
        db.session.commit()
        
        # Add piece sales for lumber bundle
        lumber_item = next(item for item in items if item.multiple_pieces)
        
        # Sale 1: 10 pieces
        sale1 = ItemSale()
        sale1.item_id = lumber_item.id
        sale1.pieces_sold = 10
        sale1.sale_price_per_piece = Decimal('4.50')
        sale1.total_sale_amount = Decimal('45.00')
        sale1.sale_date = date.today() - timedelta(days=10)
        sale1.buyer_info = 'Local contractor'
        sale1.sale_channel = 'Facebook Marketplace'
        sale1.notes = 'Pickup only'
        
        # Sale 2: 5 pieces
        sale2 = ItemSale()
        sale2.item_id = lumber_item.id
        sale2.pieces_sold = 5
        sale2.sale_price_per_piece = Decimal('5.00')
        sale2.total_sale_amount = Decimal('25.00')
        sale2.sale_date = date.today() - timedelta(days=3)
        sale2.buyer_info = 'DIY homeowner'
        sale2.sale_channel = 'Craigslist'
        
        db.session.add(sale1)
        db.session.add(sale2)
        
        # Add some expenses
        expense1 = ItemExpense()
        expense1.item_id = lumber_item.id
        expense1.description = 'Truck rental for pickup'
        expense1.amount = Decimal('35.00')
        expense1.date = date.today() - timedelta(days=20)
        expense1.category = 'transport'
        
        expense2 = ItemExpense()
        expense2.item_id = items[3].id  # drill press
        expense2.description = 'Restoration supplies'
        expense2.amount = Decimal('45.00')
        expense2.date = date.today() - timedelta(days=18)
        expense2.category = 'repair'
        
        db.session.add(expense1)
        db.session.add(expense2)
        
        # Add partner relationships
        partnership1 = ItemPartner()
        partnership1.item_id = items[4].id  # welding equipment
        partnership1.partner_id = partner1.id
        partnership1.pct_share = Decimal('30.00')
        
        partnership2 = ItemPartner()
        partnership2.item_id = items[5].id  # router
        partnership2.partner_id = partner2.id
        partnership2.pct_share = Decimal('25.00')
        
        db.session.add(partnership1)
        db.session.add(partnership2)
        
        db.session.commit()
        
        print("Demo data created successfully!")
        print(f"Created {len(items)} items across {len([auction1, auction2])} auctions")
        print(f"Created {len([partner1, partner2])} partners")
        print("You can now test the application with realistic data")

if __name__ == '__main__':
    create_demo_data()
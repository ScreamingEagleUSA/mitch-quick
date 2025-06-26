from datetime import datetime, date
from app import app, db
from models import User, Auction, Item, Partner, ItemPartner, ItemStatus

def seed_database():
    """Seed the database with sample data"""
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Note: Users are now created through Supabase authentication
        # No need to create admin user manually
        
        # Create sample partners
        if not Partner.query.first():
            partners = [
                Partner(name='John Smith', email='john@example.com'),
                Partner(name='Sarah Johnson', email='sarah@example.com'),
                Partner(name='Mike Wilson', email='mike@example.com')
            ]
            for partner in partners:
                db.session.add(partner)
        
        # Create sample auctions
        if not Auction.query.first():
            auctions = [
                Auction(
                    title='Estate Sale - Antique Furniture & Collectibles',
                    date=date(2024, 12, 15),
                    location='123 Main St, Springfield, IL',
                    url='https://example-auction.com/estate-sale-1',
                    notes='High-end estate with quality pieces'
                ),
                Auction(
                    title='Tool Liquidation Auction',
                    date=date(2024, 12, 20),
                    location='456 Industrial Way, Chicago, IL',
                    url='https://example-auction.com/tool-liquidation',
                    notes='Mix of hand tools and power tools'
                ),
                Auction(
                    title='Art & Pottery Collection',
                    date=date(2024, 12, 25),
                    location='789 Gallery St, Milwaukee, WI',
                    url='https://example-auction.com/art-pottery',
                    notes='Local artist collection with ceramics'
                )
            ]
            for auction in auctions:
                db.session.add(auction)
            
            db.session.commit()
        
        # Create sample items
        if not Item.query.first():
            auction1 = Auction.query.first()
            auction2 = Auction.query.offset(1).first()
            
            items = [
                Item(
                    auction_id=auction1.id,
                    lot_number='001',
                    title='Victorian Mahogany Dining Table',
                    description='Beautiful carved legs, seats 8 people',
                    planned_max_bid=500.00,
                    target_resale_price=800.00,
                    status=ItemStatus.SOLD,
                    purchase_price=450.00,
                    refurb_cost=50.00,
                    list_date=date(2024, 11, 1),
                    list_channel='eBay',
                    sale_date=date(2024, 11, 15),
                    sale_price=750.00,
                    sale_fees=75.00,
                    shipping_cost=25.00
                ),
                Item(
                    auction_id=auction1.id,
                    lot_number='002',
                    title='Set of China Dishes (12 place settings)',
                    description='Vintage pattern with gold trim',
                    planned_max_bid=150.00,
                    target_resale_price=300.00,
                    status=ItemStatus.LISTED,
                    purchase_price=125.00,
                    refurb_cost=0.00,
                    list_date=date(2024, 11, 20),
                    list_channel='Facebook Marketplace'
                ),
                Item(
                    auction_id=auction2.id,
                    lot_number='101',
                    title='DeWalt Circular Saw Kit',
                    description='18V cordless with 2 batteries',
                    planned_max_bid=200.00,
                    target_resale_price=350.00,
                    status=ItemStatus.WON,
                    purchase_price=180.00,
                    refurb_cost=20.00
                ),
                Item(
                    auction_id=auction2.id,
                    lot_number='102',
                    title='Vintage Hand Plane Collection',
                    description='Stanley planes in good condition',
                    planned_max_bid=100.00,
                    target_resale_price=200.00,
                    status=ItemStatus.WATCH
                )
            ]
            
            for item in items:
                db.session.add(item)
            
            db.session.commit()
        
        # Create sample item partnerships
        if not ItemPartner.query.first():
            sold_item = Item.query.filter_by(status=ItemStatus.SOLD).first()
            won_item = Item.query.filter_by(status=ItemStatus.WON).first()
            partner1 = Partner.query.first()
            partner2 = Partner.query.offset(1).first()
            
            if sold_item and partner1 and partner2:
                partnerships = [
                    ItemPartner(item_id=sold_item.id, partner_id=partner1.id, pct_share=60.0),
                    ItemPartner(item_id=sold_item.id, partner_id=partner2.id, pct_share=40.0),
                    ItemPartner(item_id=won_item.id, partner_id=partner1.id, pct_share=50.0),
                    ItemPartner(item_id=won_item.id, partner_id=partner2.id, pct_share=50.0)
                ]
                
                for partnership in partnerships:
                    db.session.add(partnership)
        
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()

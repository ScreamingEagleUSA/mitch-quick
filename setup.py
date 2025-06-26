#!/usr/bin/env python3
"""
Setup script for Mitch Quick - Auction Flipping Tracker
This script helps initialize the database and create initial data.
"""

import os
import sys
from datetime import datetime, date
from app import app, db
from models import User, Auction, Partner, Item, ItemStatus

def create_sample_data():
    """Create sample data for testing"""
    print("Creating sample data...")
    
    # Create sample auction
    auction = Auction(
        title="Sample Estate Auction",
        date=date.today() + datetime.timedelta(days=7),
        location="123 Main St, Anytown, USA",
        url="https://example.com/auction",
        notes="Sample auction for testing purposes"
    )
    db.session.add(auction)
    db.session.commit()
    
    # Create sample partner
    partner = Partner(
        name="John Doe",
        email="john@example.com"
    )
    db.session.add(partner)
    db.session.commit()
    
    # Create sample items
    items = [
        Item(
            auction_id=auction.id,
            lot_number="001",
            title="Vintage Coffee Table",
            description="Beautiful vintage coffee table in excellent condition",
            planned_max_bid=150.00,
            target_resale_price=300.00,
            status=ItemStatus.WATCH
        ),
        Item(
            auction_id=auction.id,
            lot_number="002",
            title="Antique Clock",
            description="Working antique clock from the 1920s",
            planned_max_bid=200.00,
            target_resale_price=450.00,
            status=ItemStatus.WATCH
        )
    ]
    
    for item in items:
        db.session.add(item)
    
    db.session.commit()
    print("Sample data created successfully!")

def main():
    """Main setup function"""
    print("Mitch Quick - Setup Script")
    print("=" * 40)
    
    # Check if we're in the right environment
    if not os.environ.get('SUPABASE_URL'):
        print("❌ Error: SUPABASE_URL environment variable not set")
        print("Please set up your environment variables first.")
        sys.exit(1)
    
    with app.app_context():
        try:
            # Create tables
            print("Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Note: Users are now created through Supabase authentication
            print("ℹ️  User accounts are managed through Supabase authentication")
            print("   No need to create admin users manually")
            
            # Ask if user wants sample data
            response = input("\nWould you like to create sample data? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                create_sample_data()
            
            print("\n✅ Setup completed successfully!")
            print("\nNext steps:")
            print("1. Start the application: python main.py")
            print("2. Visit http://localhost:5000")
            print("3. Sign up/in with your email through Supabase")
            
        except Exception as e:
            print(f"❌ Error during setup: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main() 
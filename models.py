from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import UniqueConstraint
from app import db

class ItemStatus(Enum):
    WATCH = 'watch'
    WON = 'won'
    LISTED = 'listed'
    SOLD = 'sold'

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime,
                           default=datetime.now,
                           onupdate=datetime.now)

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200))
    url = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('Item', backref='auction', lazy=True, cascade='all, delete-orphan')

class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    item_partnerships = db.relationship('ItemPartner', backref='partner', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'), nullable=False)
    lot_number = db.Column(db.String(50))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    planned_max_bid = db.Column(db.Numeric(10, 2))
    target_resale_price = db.Column(db.Numeric(10, 2))
    status = db.Column(db.Enum(ItemStatus), default=ItemStatus.WATCH)
    purchase_price = db.Column(db.Numeric(10, 2))
    refurb_cost = db.Column(db.Numeric(10, 2), default=0)
    list_date = db.Column(db.Date)
    list_channel = db.Column(db.String(100))
    sale_date = db.Column(db.Date)
    sale_price = db.Column(db.Numeric(10, 2))
    sale_fees = db.Column(db.Numeric(10, 2), default=0)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    ebay_suggested_price = db.Column(db.Numeric(10, 2))
    ebay_price_updated = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    partners = db.relationship('ItemPartner', backref='item', lazy=True, cascade='all, delete-orphan')
    
    @property
    def gross_profit(self):
        """Calculate gross profit (sale_price - purchase_price - refurb_cost)"""
        if not self.sale_price or not self.purchase_price:
            return None
        return float(self.sale_price) - float(self.purchase_price) - float(self.refurb_cost or 0)
    
    @property
    def net_profit(self):
        """Calculate net profit (gross_profit - sale_fees - shipping_cost)"""
        gross = self.gross_profit
        if gross is None:
            return None
        return gross - float(self.sale_fees or 0) - float(self.shipping_cost or 0)
    
    @property
    def roi_percentage(self):
        """Calculate ROI percentage"""
        if not self.purchase_price or float(self.purchase_price) == 0:
            return None
        net = self.net_profit
        if net is None:
            return None
        total_investment = float(self.purchase_price) + float(self.refurb_cost or 0)
        return (net / total_investment) * 100 if total_investment > 0 else None
    
    @property
    def break_even_price(self):
        """Calculate break-even sale price"""
        if not self.purchase_price:
            return None
        return float(self.purchase_price) + float(self.refurb_cost or 0) + float(self.sale_fees or 0) + float(self.shipping_cost or 0)

class ItemPartner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'), nullable=False)
    pct_share = db.Column(db.Numeric(5, 2), nullable=False)  # Percentage share (0-100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_partner_share(self):
        """Calculate partner's share of profit"""
        if self.item.net_profit is None:
            return None
        return (float(self.pct_share) / 100) * self.item.net_profit

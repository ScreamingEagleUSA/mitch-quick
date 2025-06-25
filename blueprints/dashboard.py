from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from models import Auction, Item, Partner, ItemPartner, ItemStatus
from utils.profit_calculations import calculate_portfolio_metrics
from utils.ebay_api import update_all_watchlist_prices
from replit_auth import require_login
from app import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@require_login
def index():
    """Main dashboard"""
    # Get all items for portfolio metrics
    all_items = Item.query.all()
    portfolio_metrics = calculate_portfolio_metrics(all_items)
    
    # Get upcoming auctions (next 30 days)
    upcoming_auctions = Auction.query.filter(
        Auction.date >= datetime.now().date(),
        Auction.date <= (datetime.now() + timedelta(days=30)).date()
    ).order_by(Auction.date).limit(5).all()
    
    # Get recent watchlist items
    recent_watchlist = Item.query.filter_by(status=ItemStatus.WATCH).order_by(
        Item.created_at.desc()
    ).limit(5).all()
    
    # Get current inventory
    current_inventory = Item.query.filter_by(status=ItemStatus.WON).order_by(
        Item.updated_at.desc()
    ).limit(5).all()
    
    # Get recent sales
    recent_sales = Item.query.filter_by(status=ItemStatus.SOLD).order_by(
        Item.sale_date.desc()
    ).limit(5).all()
    
    # Calculate partner earnings
    top_partners = []
    partners = Partner.query.all()
    for partner in partners:
        total_earnings = 0
        for partnership in partner.item_partnerships:
            if partnership.item.status == ItemStatus.SOLD:
                earnings = partnership.calculate_partner_share()
                if earnings:
                    total_earnings += earnings
        
        if total_earnings > 0:
            top_partners.append({
                'partner': partner,
                'total_earnings': total_earnings
            })
    
    top_partners.sort(key=lambda x: x['total_earnings'], reverse=True)
    top_partners = top_partners[:5]  # Top 5 partners
    
    # Weekly performance data for chart
    weekly_data = get_weekly_performance_data()
    
    return render_template('dashboard/index.html',
                         portfolio_metrics=portfolio_metrics,
                         upcoming_auctions=upcoming_auctions,
                         recent_watchlist=recent_watchlist,
                         current_inventory=current_inventory,
                         recent_sales=recent_sales,
                         top_partners=top_partners,
                         weekly_data=weekly_data)

@dashboard_bp.route('/kpis')
@login_required
def kpis():
    """Get KPI data for dashboard updates"""
    all_items = Item.query.all()
    portfolio_metrics = calculate_portfolio_metrics(all_items)
    
    return jsonify({
        'total_invested': portfolio_metrics['total_invested'],
        'total_net_profit': portfolio_metrics['total_net_profit'],
        'average_roi': portfolio_metrics['average_roi'],
        'items_sold': portfolio_metrics['items_sold'],
        'items_in_inventory': portfolio_metrics['items_in_inventory'],
        'items_listed': portfolio_metrics['items_listed'],
        'items_watchlist': portfolio_metrics['items_watchlist']
    })

@dashboard_bp.route('/update-watchlist-prices', methods=['POST'])
@login_required
def update_watchlist_prices():
    """Update eBay price suggestions for all watchlist items"""
    try:
        updated_count = update_all_watchlist_prices()
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated price suggestions for {updated_count} items'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def get_weekly_performance_data():
    """Get weekly performance data for the last 12 weeks"""
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=12)
    
    # Get all sold items in the date range
    sold_items = Item.query.filter(
        Item.status == ItemStatus.SOLD,
        Item.sale_date >= start_date.date(),
        Item.sale_date <= end_date.date()
    ).all()
    
    # Group by week
    weekly_data = {}
    for item in sold_items:
        if not item.sale_date:
            continue
            
        # Get start of week (Monday)
        week_start = item.sale_date - timedelta(days=item.sale_date.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        
        if week_key not in weekly_data:
            weekly_data[week_key] = {
                'week': week_start.strftime('%m/%d'),
                'revenue': 0,
                'profit': 0,
                'items_sold': 0
            }
        
        weekly_data[week_key]['revenue'] += float(item.sale_price or 0)
        weekly_data[week_key]['profit'] += item.net_profit or 0
        weekly_data[week_key]['items_sold'] += 1
    
    # Fill in missing weeks with zeros
    current_week = start_date.date() - timedelta(days=start_date.date().weekday())
    while current_week <= end_date.date():
        week_key = current_week.strftime('%Y-%m-%d')
        if week_key not in weekly_data:
            weekly_data[week_key] = {
                'week': current_week.strftime('%m/%d'),
                'revenue': 0,
                'profit': 0,
                'items_sold': 0
            }
        current_week += timedelta(weeks=1)
    
    # Sort by date and return as list
    return [weekly_data[key] for key in sorted(weekly_data.keys())]

@dashboard_bp.route('/quick-stats')
@login_required
def quick_stats():
    """Get quick stats for dashboard widgets"""
    # Today's stats
    today = datetime.now().date()
    
    stats = {
        'today': {
            'sales': Item.query.filter(
                Item.status == ItemStatus.SOLD,
                Item.sale_date == today
            ).count(),
            'revenue': 0,
            'new_watchlist': Item.query.filter(
                Item.status == ItemStatus.WATCH,
                func.date(Item.created_at) == today
            ).count()
        },
        'this_week': {
            'sales': 0,
            'revenue': 0,
            'profit': 0
        },
        'this_month': {
            'sales': 0,
            'revenue': 0,
            'profit': 0
        }
    }
    
    # Calculate today's revenue
    todays_sales = Item.query.filter(
        Item.status == ItemStatus.SOLD,
        Item.sale_date == today
    ).all()
    
    for sale in todays_sales:
        if sale.sale_price:
            stats['today']['revenue'] += float(sale.sale_price)
    
    # This week stats
    week_start = today - timedelta(days=today.weekday())
    week_sales = Item.query.filter(
        Item.status == ItemStatus.SOLD,
        Item.sale_date >= week_start,
        Item.sale_date <= today
    ).all()
    
    stats['this_week']['sales'] = len(week_sales)
    for sale in week_sales:
        if sale.sale_price:
            stats['this_week']['revenue'] += float(sale.sale_price)
        if sale.net_profit:
            stats['this_week']['profit'] += sale.net_profit
    
    # This month stats
    month_start = today.replace(day=1)
    month_sales = Item.query.filter(
        Item.status == ItemStatus.SOLD,
        Item.sale_date >= month_start,
        Item.sale_date <= today
    ).all()
    
    stats['this_month']['sales'] = len(month_sales)
    for sale in month_sales:
        if sale.sale_price:
            stats['this_month']['revenue'] += float(sale.sale_price)
        if sale.net_profit:
            stats['this_month']['profit'] += sale.net_profit
    
    return jsonify(stats)

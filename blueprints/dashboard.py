from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from datetime import datetime, timedelta
from supabase_auth import require_login

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@require_login
def index():
    """Main dashboard"""
    try:
        # Simple dashboard without database queries for now
        return render_template('dashboard/index.html',
                             user=current_user,
                             current_time=datetime.now())
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template('dashboard/index.html',
                             user=current_user,
                             error=str(e))

@dashboard_bp.route('/kpis')
@require_login
def kpis():
    """Get KPI data for dashboard updates"""
    return jsonify({
        'total_invested': 0,
        'total_net_profit': 0,
        'average_roi': 0,
        'items_sold': 0,
        'items_in_inventory': 0,
        'items_listed': 0,
        'items_watchlist': 0
    })

@dashboard_bp.route('/update-watchlist-prices', methods=['POST'])
@require_login
def update_watchlist_prices():
    """Update eBay price suggestions for all watchlist items"""
    return jsonify({
        'success': True,
        'updated_count': 0,
        'message': 'Feature not implemented yet'
    })

@dashboard_bp.route('/quick-stats')
@require_login
def quick_stats():
    """Get quick stats for dashboard widgets"""
    return jsonify({
        'today': {
            'sales': 0,
            'revenue': 0,
            'new_watchlist': 0
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
    })

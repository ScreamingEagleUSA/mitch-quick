from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from supabase_auth import require_login
from datetime import datetime, timedelta
import io
import csv
from models import Item, Auction, Partner, ItemPartner, ItemStatus
from utils.email_service import send_weekly_cashflow_report, generate_cashflow_csv, generate_cashflow_chart
from utils.profit_calculations import calculate_portfolio_metrics
from app import db

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@require_login
def index():
    """Reports dashboard"""
    return render_template('reports/index.html')

@reports_bp.route('/cashflow')
@require_login
def cashflow():
    """Cash flow report"""
    # Get date range from request or default to last 30 days
    end_date_str = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date_str = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('reports.index'))
    
    # Get cash flow data
    cashflow_data = get_cashflow_data(start_date, end_date)
    
    return render_template('reports/cashflow.html',
                         cashflow_data=cashflow_data,
                         start_date=start_date_str,
                         end_date=end_date_str)

@reports_bp.route('/profit-analysis')
@require_login
def profit_analysis():
    """Profit analysis report"""
    # Get all sold items
    sold_items = Item.query.filter_by(status=ItemStatus.SOLD).all()
    
    # Calculate metrics
    analysis_data = {
        'total_items': len(sold_items),
        'total_revenue': sum(float(item.sale_price) for item in sold_items if item.sale_price),
        'total_investment': sum(float(item.purchase_price) + float(item.refurb_cost or 0) 
                              for item in sold_items if item.purchase_price),
        'total_net_profit': sum(item.net_profit for item in sold_items if item.net_profit),
        'avg_roi': 0,
        'top_performers': [],
        'category_breakdown': {},
        'monthly_trends': get_monthly_profit_trends()
    }
    
    # Calculate average ROI
    roi_values = [item.roi_percentage for item in sold_items if item.roi_percentage]
    if roi_values:
        analysis_data['avg_roi'] = sum(roi_values) / len(roi_values)
    
    # Get top performing items (convert to serializable format)
    top_items = sorted(sold_items, key=lambda x: x.net_profit or 0, reverse=True)[:10]
    analysis_data['top_performers'] = [
        {
            'id': item.id,
            'title': item.title,
            'sale_price': float(item.sale_price) if item.sale_price else 0,
            'purchase_price': float(item.purchase_price) if item.purchase_price else 0,
            'net_profit': item.net_profit or 0,
            'roi_percentage': item.roi_percentage or 0,
            'auction_title': item.auction.title if item.auction else 'Unknown'
        }
        for item in top_items
    ]
    
    # Category breakdown by auction
    for item in sold_items:
        auction_title = item.auction.title if item.auction else 'Unknown'
        if auction_title not in analysis_data['category_breakdown']:
            analysis_data['category_breakdown'][auction_title] = {
                'count': 0,
                'revenue': 0,
                'profit': 0
            }
        
        analysis_data['category_breakdown'][auction_title]['count'] += 1
        if item.sale_price:
            analysis_data['category_breakdown'][auction_title]['revenue'] += float(item.sale_price)
        if item.net_profit:
            analysis_data['category_breakdown'][auction_title]['profit'] += item.net_profit
    
    return render_template('reports/profit_analysis.html', analysis_data=analysis_data)

@reports_bp.route('/partner-report')
@require_login
def partner_report():
    """Partner earnings report"""
    partners = Partner.query.all()
    partner_data = []
    
    for partner in partners:
        data = {
            'partner': partner,
            'total_items': len(partner.item_partnerships),
            'sold_items': 0,
            'total_earnings': 0,
            'pending_earnings': 0,
            'recent_sales': []
        }
        
        for partnership in partner.item_partnerships:
            if partnership.item.status == ItemStatus.SOLD:
                data['sold_items'] += 1
                earnings = partnership.calculate_partner_share()
                if earnings:
                    data['total_earnings'] += earnings
                    
                # Add to recent sales
                if len(data['recent_sales']) < 5:
                    data['recent_sales'].append({
                        'item': partnership.item,
                        'share': earnings,
                        'percentage': partnership.pct_share
                    })
            elif partnership.item.status in [ItemStatus.WON, ItemStatus.LISTED]:
                # Estimate pending earnings
                if partnership.item.target_resale_price and partnership.item.purchase_price:
                    estimated_net = float(partnership.item.target_resale_price) - float(partnership.item.purchase_price)
                    estimated_net -= float(partnership.item.refurb_cost or 0)
                    estimated_net -= estimated_net * 0.15  # Estimate fees
                    if estimated_net > 0:
                        data['pending_earnings'] += (float(partnership.pct_share) / 100) * estimated_net
        
        # Sort recent sales by date
        data['recent_sales'].sort(key=lambda x: x['item'].sale_date or datetime.min.date(), reverse=True)
        partner_data.append(data)
    
    # Sort by total earnings
    partner_data.sort(key=lambda x: x['total_earnings'], reverse=True)
    
    return render_template('reports/partner_report.html', partner_data=partner_data)

@reports_bp.route('/export/cashflow')
@require_login
def export_cashflow():
    """Export cash flow report as CSV"""
    start_date_str = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('reports.cashflow'))
    
    # Generate CSV
    csv_data = generate_cashflow_csv(start_date, end_date)
    
    if not csv_data:
        flash('No data available for the selected date range.', 'warning')
        return redirect(url_for('reports.cashflow'))
    
    # Return CSV file
    output = io.BytesIO()
    output.write(csv_data.encode('utf-8'))
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'cashflow_report_{start_date_str}_{end_date_str}.csv'
    )

@reports_bp.route('/export/profit-analysis')
@require_login
def export_profit_analysis():
    """Export profit analysis as CSV"""
    sold_items = Item.query.filter_by(status=ItemStatus.SOLD).all()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Sale Date', 'Auction', 'Lot Number', 'Item Title',
        'Purchase Price', 'Refurb Cost', 'Sale Price',
        'Sale Fees', 'Shipping Cost', 'Gross Profit',
        'Net Profit', 'ROI %', 'List Channel'
    ])
    
    # Data
    for item in sold_items:
        writer.writerow([
            item.sale_date.strftime('%Y-%m-%d') if item.sale_date else '',
            item.auction.title if item.auction else '',
            item.lot_number or '',
            item.title,
            f'${float(item.purchase_price):.2f}' if item.purchase_price else '',
            f'${float(item.refurb_cost):.2f}' if item.refurb_cost else '$0.00',
            f'${float(item.sale_price):.2f}' if item.sale_price else '',
            f'${float(item.sale_fees):.2f}' if item.sale_fees else '$0.00',
            f'${float(item.shipping_cost):.2f}' if item.shipping_cost else '$0.00',
            f'${item.gross_profit:.2f}' if item.gross_profit else '',
            f'${item.net_profit:.2f}' if item.net_profit else '',
            f'{item.roi_percentage:.1f}%' if item.roi_percentage else '',
            item.list_channel or ''
        ])
    
    output.seek(0)
    
    # Return CSV file
    csv_bytes = io.BytesIO()
    csv_bytes.write(output.getvalue().encode('utf-8'))
    csv_bytes.seek(0)
    
    return send_file(
        csv_bytes,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'profit_analysis_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@reports_bp.route('/send-weekly-report', methods=['POST'])
@require_login
def send_weekly_report():
    """Send weekly cash flow report via email"""
    recipient_emails = request.form.get('emails', '').split(',')
    recipient_emails = [email.strip() for email in recipient_emails if email.strip()]
    
    if not recipient_emails:
        return jsonify({'success': False, 'error': 'No email addresses provided'})
    
    try:
        success = send_weekly_cashflow_report(recipient_emails)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Weekly report sent to {len(recipient_emails)} recipients'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send email report'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def get_cashflow_data(start_date, end_date):
    """Get cash flow data for the specified date range"""
    # Get all items updated in the date range
    items = Item.query.filter(
        Item.updated_at >= start_date,
        Item.updated_at <= end_date
    ).all()
    
    transactions = []
    total_income = 0
    total_expenses = 0
    
    for item in items:
        auction_title = item.auction.title if item.auction else 'N/A'
        
        # Purchase transactions
        if item.purchase_price:
            transactions.append({
                'date': item.updated_at.date() if item.updated_at else start_date.date(),
                'type': 'Expense',
                'category': 'Purchase',
                'item': item.title,
                'amount': -float(item.purchase_price),
                'auction': auction_title,
                'description': f'Lot #{item.lot_number}' if item.lot_number else ''
            })
            total_expenses += float(item.purchase_price)
        
        # Refurbishment costs
        if item.refurb_cost and float(item.refurb_cost) > 0:
            transactions.append({
                'date': item.updated_at.date() if item.updated_at else start_date.date(),
                'type': 'Expense',
                'category': 'Refurbishment',
                'item': item.title,
                'amount': -float(item.refurb_cost),
                'auction': auction_title,
                'description': 'Repair/restoration costs'
            })
            total_expenses += float(item.refurb_cost)
        
        # Sales income
        if item.sale_price and item.status == ItemStatus.SOLD:
            transactions.append({
                'date': item.sale_date if item.sale_date else item.updated_at.date(),
                'type': 'Income',
                'category': 'Sale',
                'item': item.title,
                'amount': float(item.sale_price),
                'auction': auction_title,
                'description': f'Sold on {item.list_channel}' if item.list_channel else 'Sale'
            })
            total_income += float(item.sale_price)
            
            # Sale fees
            if item.sale_fees and float(item.sale_fees) > 0:
                transactions.append({
                    'date': item.sale_date if item.sale_date else item.updated_at.date(),
                    'type': 'Expense',
                    'category': 'Fees',
                    'item': item.title,
                    'amount': -float(item.sale_fees),
                    'auction': auction_title,
                    'description': 'Marketplace fees'
                })
                total_expenses += float(item.sale_fees)
            
            # Shipping costs
            if item.shipping_cost and float(item.shipping_cost) > 0:
                transactions.append({
                    'date': item.sale_date if item.sale_date else item.updated_at.date(),
                    'type': 'Expense',
                    'category': 'Shipping',
                    'item': item.title,
                    'amount': -float(item.shipping_cost),
                    'auction': auction_title,
                    'description': 'Shipping costs'
                })
                total_expenses += float(item.shipping_cost)
    
    # Sort transactions by date
    transactions.sort(key=lambda x: x['date'], reverse=True)
    
    return {
        'transactions': transactions,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_cashflow': total_income - total_expenses,
        'summary': {
            'total_transactions': len(transactions),
            'income_transactions': len([t for t in transactions if t['type'] == 'Income']),
            'expense_transactions': len([t for t in transactions if t['type'] == 'Expense'])
        }
    }

def get_monthly_profit_trends():
    """Get monthly profit trends for the last 12 months"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Get sold items in the last 12 months
    sold_items = Item.query.filter(
        Item.status == ItemStatus.SOLD,
        Item.sale_date >= start_date.date(),
        Item.sale_date <= end_date.date()
    ).all()
    
    monthly_data = {}
    
    for item in sold_items:
        if not item.sale_date:
            continue
            
        month_key = item.sale_date.strftime('%Y-%m')
        
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'month': item.sale_date.strftime('%B %Y'),
                'revenue': 0,
                'profit': 0,
                'items': 0
            }
        
        monthly_data[month_key]['revenue'] += float(item.sale_price or 0)
        monthly_data[month_key]['profit'] += item.net_profit or 0
        monthly_data[month_key]['items'] += 1
    
    # Sort by month and return as list
    return [monthly_data[key] for key in sorted(monthly_data.keys())]

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from replit_auth import require_login
from datetime import datetime
from models import Partner, ItemPartner, Item, ItemStatus
from app import db

partners_bp = Blueprint('partners', __name__)

@partners_bp.route('/')
@login_required
def index():
    """List all partners"""
    partners = Partner.query.order_by(Partner.name).all()
    
    # Calculate partner statistics
    partner_stats = {}
    for partner in partners:
        stats = {
            'total_items': 0,
            'sold_items': 0,
            'total_earnings': 0,
            'pending_earnings': 0
        }
        
        for partnership in partner.item_partnerships:
            stats['total_items'] += 1
            
            if partnership.item.status == ItemStatus.SOLD:
                stats['sold_items'] += 1
                earnings = partnership.calculate_partner_share()
                if earnings:
                    stats['total_earnings'] += earnings
            elif partnership.item.status in [ItemStatus.WON, ItemStatus.LISTED]:
                # Estimate pending earnings based on target resale price
                if partnership.item.target_resale_price and partnership.item.purchase_price:
                    estimated_net = float(partnership.item.target_resale_price) - float(partnership.item.purchase_price)
                    estimated_net -= float(partnership.item.refurb_cost or 0)
                    estimated_net -= estimated_net * 0.15  # Estimate 15% for fees/shipping
                    if estimated_net > 0:
                        stats['pending_earnings'] += (float(partnership.pct_share) / 100) * estimated_net
        
        partner_stats[partner.id] = stats
    
    return render_template('partners/index.html', partners=partners, partner_stats=partner_stats)

@partners_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new partner"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Validation
        if not name:
            flash('Name is required.', 'danger')
            return render_template('partners/form.html')
        
        # Check if partner exists
        if Partner.query.filter_by(name=name).first():
            flash('Partner with this name already exists.', 'danger')
            return render_template('partners/form.html')
        
        # Create partner
        partner = Partner(name=name, email=email)
        
        try:
            db.session.add(partner)
            db.session.commit()
            flash('Partner created successfully!', 'success')
            return redirect(url_for('partners.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating partner. Please try again.', 'danger')
    
    return render_template('partners/form.html')

@partners_bp.route('/<int:partner_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(partner_id):
    """Edit partner"""
    partner = Partner.query.get_or_404(partner_id)
    
    if request.method == 'POST':
        partner.name = request.form.get('name')
        partner.email = request.form.get('email')
        
        # Validation
        if not partner.name:
            flash('Name is required.', 'danger')
            return render_template('partners/form.html', partner=partner)
        
        # Check if another partner has this name
        existing = Partner.query.filter(Partner.name == partner.name, Partner.id != partner_id).first()
        if existing:
            flash('Another partner with this name already exists.', 'danger')
            return render_template('partners/form.html', partner=partner)
        
        try:
            db.session.commit()
            flash('Partner updated successfully!', 'success')
            return redirect(url_for('partners.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating partner. Please try again.', 'danger')
    
    return render_template('partners/form.html', partner=partner)

@partners_bp.route('/<int:partner_id>/delete', methods=['POST'])
@login_required
def delete(partner_id):
    """Delete partner"""
    partner = Partner.query.get_or_404(partner_id)
    
    # Check if partner has partnerships
    if partner.item_partnerships:
        flash('Cannot delete partner with existing partnerships. Remove partnerships first.', 'danger')
        return redirect(url_for('partners.index'))
    
    try:
        db.session.delete(partner)
        db.session.commit()
        flash('Partner deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting partner. Please try again.', 'danger')
    
    return redirect(url_for('partners.index'))

@partners_bp.route('/<int:partner_id>/view')
@login_required
def view(partner_id):
    """View partner details and earnings"""
    partner = Partner.query.get_or_404(partner_id)
    
    # Get all partnerships for this partner
    partnerships = ItemPartner.query.filter_by(partner_id=partner_id).join(Item).order_by(Item.updated_at.desc()).all()
    
    # Calculate detailed earnings
    earnings_data = []
    total_earnings = 0
    pending_earnings = 0
    
    for partnership in partnerships:
        item = partnership.item
        data = {
            'item': item,
            'partnership': partnership,
            'share_amount': None,
            'status': item.status.value
        }
        
        if item.status == ItemStatus.SOLD and item.net_profit:
            share_amount = partnership.calculate_partner_share()
            if share_amount:
                data['share_amount'] = share_amount
                total_earnings += share_amount
        elif item.status in [ItemStatus.WON, ItemStatus.LISTED] and item.target_resale_price and item.purchase_price:
            # Estimate pending earnings
            estimated_net = float(item.target_resale_price) - float(item.purchase_price)
            estimated_net -= float(item.refurb_cost or 0)
            estimated_net -= estimated_net * 0.15  # Estimate fees
            if estimated_net > 0:
                estimated_share = (float(partnership.pct_share) / 100) * estimated_net
                data['estimated_share'] = estimated_share
                pending_earnings += estimated_share
        
        earnings_data.append(data)
    
    return render_template('partners/view.html', 
                         partner=partner, 
                         earnings_data=earnings_data,
                         total_earnings=total_earnings,
                         pending_earnings=pending_earnings)

@partners_bp.route('/<int:partner_id>/earnings/export')
@login_required
def export_earnings(partner_id):
    """Export partner earnings as CSV"""
    partner = Partner.query.get_or_404(partner_id)
    
    # Get all sold partnerships for this partner
    partnerships = ItemPartner.query.filter_by(partner_id=partner_id).join(Item).filter(
        Item.status == ItemStatus.SOLD
    ).order_by(Item.sale_date.desc()).all()
    
    # Generate CSV content
    import io
    import csv
    from flask import Response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Sale Date', 'Item Title', 'Lot Number', 'Auction', 
        'Purchase Price', 'Sale Price', 'Net Profit', 
        'Partner Share %', 'Partner Earnings'
    ])
    
    # Write data
    total_earnings = 0
    for partnership in partnerships:
        item = partnership.item
        share_amount = partnership.calculate_partner_share()
        
        if share_amount:
            total_earnings += share_amount
        
        writer.writerow([
            item.sale_date.strftime('%Y-%m-%d') if item.sale_date else '',
            item.title,
            item.lot_number or '',
            item.auction.title if item.auction else '',
            f'${float(item.purchase_price):.2f}' if item.purchase_price else '',
            f'${float(item.sale_price):.2f}' if item.sale_price else '',
            f'${item.net_profit:.2f}' if item.net_profit else '',
            f'{float(partnership.pct_share):.1f}%',
            f'${share_amount:.2f}' if share_amount else ''
        ])
    
    # Add total row
    writer.writerow(['', '', '', '', '', '', '', 'Total:', f'${total_earnings:.2f}'])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{partner.name}_earnings_{datetime.now().strftime("%Y%m%d")}.csv"'
        }
    )

@partners_bp.route('/earnings')
@login_required
def earnings_summary():
    """Show earnings summary for all partners"""
    partners = Partner.query.order_by(Partner.name).all()
    
    summary_data = []
    for partner in partners:
        # Calculate total earnings
        total_earnings = 0
        total_items = 0
        sold_items = 0
        
        for partnership in partner.item_partnerships:
            total_items += 1
            
            if partnership.item.status == ItemStatus.SOLD:
                sold_items += 1
                earnings = partnership.calculate_partner_share()
                if earnings:
                    total_earnings += earnings
        
        summary_data.append({
            'partner': partner,
            'total_earnings': total_earnings,
            'total_items': total_items,
            'sold_items': sold_items
        })
    
    # Sort by total earnings
    summary_data.sort(key=lambda x: x['total_earnings'], reverse=True)
    
    return render_template('partners/earnings.html', summary_data=summary_data)

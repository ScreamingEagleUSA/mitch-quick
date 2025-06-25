from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from replit_auth import require_login
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from models import Item, Auction, Partner, ItemPartner, ItemStatus, ItemExpense, ItemSale
from utils.ebay_api import ebay_api
from app import db

items_bp = Blueprint('items', __name__)

@items_bp.route('/')
@require_login
def index():
    """List all items with filtering"""
    status_filter = request.args.get('status', 'all')
    auction_filter = request.args.get('auction', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Item.query
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter(Item.status == ItemStatus(status_filter))
    
    if auction_filter != 'all':
        query = query.filter(Item.auction_id == int(auction_filter))
    
    items = query.order_by(Item.updated_at.desc()).all()
    
    # Get auctions for filter dropdown
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    
    return render_template('items/index.html', 
                         items=items, 
                         auctions=auctions,
                         status_filter=status_filter,
                         auction_filter=auction_filter)

@items_bp.route('/bulk-action', methods=['POST'])
@require_login
def bulk_action():
    """Handle bulk actions on items"""
    action = request.form.get('action')
    selected_items = request.form.getlist('selected_items')
    
    if not selected_items:
        flash('No items selected.', 'warning')
        return redirect(url_for('items.index'))
    
    if action == 'delete':
        try:
            deleted_count = 0
            for item_id in selected_items:
                item = Item.query.get(int(item_id))
                if item:
                    # Delete partnerships first
                    ItemPartner.query.filter_by(item_id=item.id).delete()
                    db.session.delete(item)
                    deleted_count += 1
            
            db.session.commit()
            flash(f'Successfully deleted {deleted_count} items.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting items: {str(e)}', 'danger')
    
    elif action == 'status_change':
        new_status = request.form.get('new_status')
        if new_status and new_status in [status.value for status in ItemStatus]:
            try:
                updated_count = 0
                for item_id in selected_items:
                    item = Item.query.get(int(item_id))
                    if item:
                        item.status = ItemStatus(new_status)
                        updated_count += 1
                
                db.session.commit()
                flash(f'Successfully updated {updated_count} items to {new_status}.', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating items: {str(e)}', 'danger')
        else:
            flash('Invalid status selected.', 'danger')
    
    return redirect(url_for('items.index'))

@items_bp.route('/create', methods=['GET', 'POST'])
@require_login
def create():
    """Create new item"""
    if request.method == 'POST':
        try:
            # Get all form data
            auction_id = request.form.get('auction_id')
            title = request.form.get('title')
            
            # Validation
            if not auction_id or not title:
                flash('Auction and title are required.', 'danger')
                return render_template('items/form.html', auctions=Auction.query.all())
            
            # Create item with all form fields
            item = Item(
                auction_id=int(auction_id),
                lot_number=request.form.get('lot_number') or None,
                title=title,
                description=request.form.get('description') or None,
                planned_max_bid=float(request.form.get('planned_max_bid')) if request.form.get('planned_max_bid') else None,
                target_resale_price=float(request.form.get('target_resale_price')) if request.form.get('target_resale_price') else None,
                status=ItemStatus(request.form.get('status', 'watch')),
                purchase_price=float(request.form.get('purchase_price')) if request.form.get('purchase_price') else None,
                refurb_cost=float(request.form.get('refurb_cost')) if request.form.get('refurb_cost') else None,
                list_channel=request.form.get('list_channel') or None,
                sale_price=float(request.form.get('sale_price')) if request.form.get('sale_price') else None,
                sale_fees=float(request.form.get('sale_fees')) if request.form.get('sale_fees') else None,
                shipping_cost=float(request.form.get('shipping_cost')) if request.form.get('shipping_cost') else None,
                
                # Multiple pieces functionality
                multiple_pieces=request.form.get('multiple_pieces') == 'on',
                pieces_total=int(request.form.get('pieces_total')) if request.form.get('pieces_total') else None
            )
            
            # Handle dates
            list_date_str = request.form.get('list_date')
            if list_date_str:
                item.list_date = datetime.strptime(list_date_str, '%Y-%m-%d').date()
            
            sale_date_str = request.form.get('sale_date')
            if sale_date_str:
                item.sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d').date()
            
            db.session.add(item)
            db.session.commit()
            
            # Try to get eBay price suggestion (non-blocking)
            try:
                ebay_api.update_item_price_suggestion(item)
            except:
                pass  # Don't fail item creation if eBay API fails
            
            flash('Item created successfully! You can now add partners if needed.', 'success')
            return redirect(url_for('items.edit', item_id=item.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating item: {str(e)}', 'danger')
    
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    return render_template('items/form.html', auctions=auctions)

@items_bp.route('/<int:item_id>/edit', methods=['GET', 'POST'])
@require_login
def edit(item_id):
    """Edit item"""
    item = Item.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.auction_id = int(request.form.get('auction_id'))
        item.lot_number = request.form.get('lot_number')
        item.title = request.form.get('title')
        item.description = request.form.get('description')
        item.planned_max_bid = float(request.form.get('planned_max_bid')) if request.form.get('planned_max_bid') else None
        item.target_resale_price = float(request.form.get('target_resale_price')) if request.form.get('target_resale_price') else None
        item.status = ItemStatus(request.form.get('status'))
        
        # Purchase details
        item.purchase_price = float(request.form.get('purchase_price')) if request.form.get('purchase_price') else None
        item.refurb_cost = float(request.form.get('refurb_cost')) if request.form.get('refurb_cost') else None
        
        # Listing details
        list_date_str = request.form.get('list_date')
        if list_date_str:
            item.list_date = datetime.strptime(list_date_str, '%Y-%m-%d').date()
        item.list_channel = request.form.get('list_channel')
        
        # Sale details  
        sale_date_str = request.form.get('sale_date')
        item.sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d').date() if sale_date_str else None
        item.sale_price = float(request.form.get('sale_price')) if request.form.get('sale_price') else None
        item.sale_fees = float(request.form.get('sale_fees')) if request.form.get('sale_fees') else 0
        item.shipping_cost = float(request.form.get('shipping_cost')) if request.form.get('shipping_cost') else 0
        
        # Handle multiple pieces functionality
        multiple_pieces = request.form.get('multiple_pieces') == 'on'
        pieces_total = request.form.get('pieces_total')
        
        item.multiple_pieces = multiple_pieces
        if multiple_pieces and pieces_total:
            pieces_total_int = int(pieces_total)
            item.pieces_total = pieces_total_int
            # Only set pieces_remaining if it's not already set
            if item.pieces_remaining is None:
                item.pieces_remaining = pieces_total_int
        elif not multiple_pieces:
            item.multiple_pieces = False
            item.pieces_total = None
            item.pieces_remaining = None
        if sale_date_str:
            item.sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d').date()
        item.sale_price = float(request.form.get('sale_price')) if request.form.get('sale_price') else None
        item.sale_fees = float(request.form.get('sale_fees')) if request.form.get('sale_fees') else None
        item.shipping_cost = float(request.form.get('shipping_cost')) if request.form.get('shipping_cost') else None
        
        # Validation
        if not item.title:
            flash('Title is required.', 'danger')
            return render_template('items/form.html', item=item, auctions=Auction.query.all())
        
        try:
            item.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('items.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating item. Please try again.', 'danger')
    
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    return render_template('items/form.html', item=item, auctions=auctions)

@items_bp.route('/<int:item_id>/delete', methods=['POST'])
@require_login
def delete(item_id):
    """Delete item"""
    item = Item.query.get_or_404(item_id)
    
    try:
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting item. Please try again.', 'danger')
    
    return redirect(url_for('items.index'))

@items_bp.route('/<int:item_id>/partners', methods=['GET', 'POST'])
@require_login
def manage_partners(item_id):
    """Manage item partners"""
    item = Item.query.get_or_404(item_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_partner':
            # Handle adding partner share
            partner_id = request.form.get('partner_id')
            pct_share = request.form.get('pct_share')
            
            if partner_id and pct_share:
                try:
                    # Check if partnership already exists
                    existing = ItemPartner.query.filter_by(
                        item_id=item_id,
                        partner_id=int(partner_id)
                    ).first()
                    
                    if existing:
                        existing.pct_share = float(pct_share)
                        flash('Partner share updated successfully!', 'success')
                    else:
                        partnership = ItemPartner(
                            item_id=item_id,
                            partner_id=int(partner_id),
                            pct_share=float(pct_share)
                        )
                        db.session.add(partnership)
                        flash('Partner added successfully!', 'success')
                    
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash('Error updating partner share. Please try again.', 'danger')
        
        elif action == 'remove_partner':
            # Handle removing partner
            partnership_id = request.form.get('partnership_id')
            if partnership_id:
                try:
                    partnership = ItemPartner.query.get(int(partnership_id))
                    if partnership:
                        db.session.delete(partnership)
                        db.session.commit()
                        flash('Partner removed successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash('Error removing partner. Please try again.', 'danger')
        
        return redirect(url_for('items.manage_partners', item_id=item_id))
    
    try:
        # Get all partners and existing partnerships
        partners = Partner.query.all()
        existing_partnerships = ItemPartner.query.filter_by(item_id=item_id).all()
        
        # Calculate total percentage
        total_percentage = sum(float(p.pct_share) for p in existing_partnerships) if existing_partnerships else 0.0
        
        return render_template('items/partners.html', 
                             item=item, 
                             partners=partners, 
                             existing_partnerships=existing_partnerships,
                             total_percentage=total_percentage)
    except Exception as e:
        flash(f'Error loading partner management: {str(e)}', 'danger')
        return redirect(url_for('items.edit', item_id=item_id))

@items_bp.route('/watchlist')
@require_login
def watchlist():
    """Show watchlist items"""
    items = Item.query.filter_by(status=ItemStatus.WATCH).order_by(Item.updated_at.desc()).all()
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    
    return render_template('items/watchlist.html', items=items, auctions=auctions)

@items_bp.route('/inventory')
@require_login
def inventory():
    """Show inventory (won items)"""
    items = Item.query.filter_by(status=ItemStatus.WON).order_by(Item.updated_at.desc()).all()
    
    return render_template('items/inventory.html', items=items)

@items_bp.route('/sold')
@require_login
def sold():
    """Show sold items"""
    items = Item.query.filter_by(status=ItemStatus.SOLD).order_by(Item.sale_date.desc(), Item.updated_at.desc()).all()
    
    return render_template('items/sold.html', items=items)

@items_bp.route('/export-inventory')
@require_login
def export_inventory():
    """Export inventory as CSV"""
    import csv
    import io
    from flask import make_response
    
    # Get all items 
    items = Item.query.order_by(Item.updated_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Title', 'Lot Number', 'Auction', 'Status', 'Purchase Price', 
        'Refurb Cost', 'Target Resale', 'Sale Price', 'Sale Date', 'Net Profit', 'ROI %'
    ])
    
    # Write data
    for item in items:
        writer.writerow([
            item.id,
            item.title,
            item.lot_number or '',
            item.auction.title if item.auction else '',
            item.status.value,
            float(item.purchase_price) if item.purchase_price else '',
            float(item.refurb_cost) if item.refurb_cost else '',
            float(item.target_resale_price) if item.target_resale_price else '',
            float(item.sale_price) if item.sale_price else '',
            item.sale_date.strftime('%Y-%m-%d') if item.sale_date else '',
            item.net_profit if item.net_profit else '',
            round(item.roi_percentage, 2) if item.roi_percentage else ''
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=inventory.csv'
    
    return response

@items_bp.route('/import-inventory', methods=['GET', 'POST'])
@require_login
def import_inventory():
    """Import/update inventory from CSV"""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No CSV file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No CSV file selected.', 'danger')
            return redirect(request.url)
        
        if not file.filename.lower().endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(request.url)
        
        try:
            import csv
            import io
            from datetime import datetime
            
            # Read CSV content
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            updated_count = 0
            
            for row in csv_input:
                item_id = row.get('ID', '').strip()
                
                if item_id:
                    # Update existing item
                    item = Item.query.get(int(item_id))
                    if item:
                        if row.get('Purchase Price'):
                            item.purchase_price = float(row['Purchase Price'])
                        if row.get('Refurb Cost'):
                            item.refurb_cost = float(row['Refurb Cost'])
                        if row.get('Sale Price'):
                            item.sale_price = float(row['Sale Price'])
                        if row.get('Sale Date'):
                            item.sale_date = datetime.strptime(row['Sale Date'], '%Y-%m-%d').date()
                        
                        item.updated_at = datetime.utcnow()
                        updated_count += 1
                
            db.session.commit()
            
            flash(f'Successfully updated {updated_count} items from CSV.', 'success')
            return redirect(url_for('items.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing CSV: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('items/import_inventory.html')

@items_bp.route('/<int:item_id>/update-price', methods=['POST'])
@require_login
def update_price_suggestion(item_id):
    """Update eBay price suggestion for item"""
    item = Item.query.get_or_404(item_id)
    
    try:
        success = ebay_api.update_item_price_suggestion(item)
        
        if success:
            return jsonify({
                'success': True,
                'suggested_price': float(item.ebay_suggested_price) if item.ebay_suggested_price else None,
                'updated_at': item.ebay_price_updated.strftime('%Y-%m-%d %H:%M') if item.ebay_price_updated else None
            })
        else:
            return jsonify({'success': False, 'error': 'Could not fetch price suggestion'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@items_bp.route('/<int:item_id>/view')
@require_login
def view(item_id):
    """View item details"""
    item = Item.query.get_or_404(item_id)
    return render_template('items/view.html', item=item)

@items_bp.route('/<int:item_id>/sell-pieces', methods=['GET', 'POST'])
@require_login
def sell_pieces(item_id):
    """Sell pieces from a multiple-piece item"""
    item = Item.query.get_or_404(item_id)
    
    if not item.multiple_pieces:
        flash('This item is not configured for multiple pieces sales.', 'warning')
        return redirect(url_for('items.view', item_id=item_id))
    
    if request.method == 'POST':
        try:
            pieces_sold = int(request.form.get('pieces_sold', 0))
            sale_price_per_piece = float(request.form.get('sale_price_per_piece', 0))
            sale_date_str = request.form.get('sale_date')
            buyer_info = request.form.get('buyer_info', '').strip()
            sale_channel = request.form.get('sale_channel', '').strip()
            notes = request.form.get('notes', '').strip()
            
            if pieces_sold <= 0:
                flash('Number of pieces sold must be greater than 0.', 'danger')
                return redirect(request.url)
            
            if pieces_sold > item.pieces_remaining:
                flash(f'Cannot sell {pieces_sold} pieces. Only {item.pieces_remaining} pieces remaining.', 'danger')
                return redirect(request.url)
            
            if sale_price_per_piece <= 0:
                flash('Sale price per piece must be greater than 0.', 'danger')
                return redirect(request.url)
            
            # Create the sale record
            sale = ItemSale(
                item_id=item.id,
                pieces_sold=pieces_sold,
                sale_price_per_piece=sale_price_per_piece,
                total_sale_amount=pieces_sold * sale_price_per_piece,
                sale_date=datetime.strptime(sale_date_str, '%Y-%m-%d').date() if sale_date_str else datetime.utcnow().date(),
                buyer_info=buyer_info,
                sale_channel=sale_channel,
                notes=notes
            )
            
            # Update remaining pieces
            item.pieces_remaining = item.pieces_remaining - pieces_sold
            
            # If all pieces are sold, update item status
            if item.pieces_remaining == 0:
                item.status = ItemStatus.SOLD
            
            db.session.add(sale)
            db.session.commit()
            
            flash(f'Successfully sold {pieces_sold} pieces for ${sale_price_per_piece:.2f} each. Total: ${sale.total_sale_amount:.2f}', 'success')
            return redirect(url_for('items.view', item_id=item_id))
            
        except ValueError as e:
            flash('Please enter valid numbers for pieces and price.', 'danger')
            return redirect(request.url)
        except Exception as e:
            flash(f'Error recording sale: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('items/sell_pieces.html', item=item, datetime=datetime)


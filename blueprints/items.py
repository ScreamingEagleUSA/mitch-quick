from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from replit_auth import require_login
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from models import Item, Auction, Partner, ItemPartner, ItemStatus
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
                shipping_cost=float(request.form.get('shipping_cost')) if request.form.get('shipping_cost') else None
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

# PDF import functionality removed per user request
    """Import items from PDF lot sheet"""
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flash('No PDF file selected.', 'danger')
            return redirect(request.url)
        
        file = request.files['pdf_file']
        auction_id = request.form.get('auction_id')
        
        if not file or file.filename == '':
            flash('No PDF file selected.', 'danger')
            return redirect(request.url)
        
        if not auction_id:
            flash('Please select an auction.', 'danger')
            return redirect(request.url)
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            flash('Please upload a PDF file.', 'danger')
            return redirect(request.url)
        
        try:
            # Process PDF
            lots = process_uploaded_pdf(file, file.filename)
            
            if not lots:
                flash('No lots could be extracted from the PDF. Please check the file format.', 'warning')
                return redirect(request.url)
            
            # Store in a temporary file instead of session to avoid size limits
            import tempfile
            import json
            import os

            
            # Create temp file for lots data
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', prefix='import_')
            try:
                with os.fdopen(temp_fd, 'w') as tmp_file:
                    json.dump({
                        'auction_id': auction_id,
                        'lots': lots
                    }, tmp_file)
                
                # Store just the filename in session
                session['import_temp_file'] = os.path.basename(temp_path)
                
                flash(f'Successfully parsed {len(lots)} lots from PDF.', 'success')
                return redirect(url_for('items.import_preview'))
            except Exception as e:
                os.unlink(temp_path)
                raise e
            
        except Exception as e:
            flash(f'Error processing PDF: {str(e)}', 'danger')
            return redirect(request.url)
    
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    return render_template('items/import.html', auctions=auctions)

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

@items_bp.route('/watchlist')
@require_login
def watchlist():
    """Show watchlist items"""
    items = Item.query.filter_by(status=ItemStatus.WATCH).order_by(Item.created_at.desc()).all()
    return render_template('items/watchlist.html', items=items)

@items_bp.route('/inventory')
@require_login
def inventory():
    """Show inventory (won items)"""
    items = Item.query.filter_by(status=ItemStatus.WON).order_by(Item.updated_at.desc()).all()
    return render_template('items/inventory.html', items=items)

@items_bp.route('/inventory/export')
@require_login
def export_inventory():
    """Export inventory as CSV"""
    import csv
    import io
    from flask import make_response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Auction', 'Lot Number', 'Title', 'Description', 
        'Purchase Price', 'Refurb Cost', 'Status', 'Target Resale Price',
        'List Date', 'List Channel', 'Sale Date', 'Sale Price', 'Sale Fees',
        'Shipping Cost', 'eBay Suggested Price', 'Created At'
    ])
    
    # Write data
    items = Item.query.all()
    for item in items:
        writer.writerow([
            item.id,
            item.auction.title if item.auction else '',
            item.lot_number or '',
            item.title,
            item.description or '',
            float(item.purchase_price) if item.purchase_price else '',
            float(item.refurb_cost) if item.refurb_cost else 0,
            item.status.value if item.status else '',
            float(item.target_resale_price) if item.target_resale_price else '',
            item.list_date.strftime('%Y-%m-%d') if item.list_date else '',
            item.list_channel or '',
            item.sale_date.strftime('%Y-%m-%d') if item.sale_date else '',
            float(item.sale_price) if item.sale_price else '',
            float(item.sale_fees) if item.sale_fees else 0,
            float(item.shipping_cost) if item.shipping_cost else 0,
            float(item.ebay_suggested_price) if item.ebay_suggested_price else '',
            item.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=inventory_export.csv'
    
    return response

@items_bp.route('/sold')
@require_login
def sold():
    """Show sold items"""
    items = Item.query.filter_by(status=ItemStatus.SOLD).order_by(Item.sale_date.desc()).all()
    return render_template('items/sold.html', items=items)

@items_bp.route('/<int:item_id>')
@require_login
def view(item_id):
    """View item details"""
    item = Item.query.get_or_404(item_id)
    return render_template('items/view.html', item=item)

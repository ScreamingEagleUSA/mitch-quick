from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from models import Item, Auction, Partner, ItemPartner, ItemStatus
from utils.ocr_parser import process_uploaded_pdf
from utils.ebay_api import ebay_api
from app import db

items_bp = Blueprint('items', __name__)

@items_bp.route('/')
@login_required
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
    
    items = query.order_by(Item.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get auctions for filter dropdown
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    
    return render_template('items/index.html', 
                         items=items, 
                         auctions=auctions,
                         status_filter=status_filter,
                         auction_filter=auction_filter)

@items_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new item"""
    if request.method == 'POST':
        auction_id = request.form.get('auction_id')
        lot_number = request.form.get('lot_number')
        title = request.form.get('title')
        description = request.form.get('description')
        planned_max_bid = request.form.get('planned_max_bid')
        target_resale_price = request.form.get('target_resale_price')
        
        # Validation
        if not auction_id or not title:
            flash('Auction and title are required.', 'danger')
            return render_template('items/form.html', auctions=Auction.query.all())
        
        # Create item
        item = Item(
            auction_id=int(auction_id),
            lot_number=lot_number,
            title=title,
            description=description,
            planned_max_bid=float(planned_max_bid) if planned_max_bid else None,
            target_resale_price=float(target_resale_price) if target_resale_price else None,
            status=ItemStatus.WATCH
        )
        
        try:
            db.session.add(item)
            db.session.commit()
            
            # Try to get eBay price suggestion
            ebay_api.update_item_price_suggestion(item)
            
            flash('Item created successfully!', 'success')
            return redirect(url_for('items.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating item. Please try again.', 'danger')
    
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    return render_template('items/form.html', auctions=auctions)

@items_bp.route('/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
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
@login_required
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
@login_required
def manage_partners(item_id):
    """Manage item partners"""
    item = Item.query.get_or_404(item_id)
    
    if request.method == 'POST':
        # Clear existing partnerships
        ItemPartner.query.filter_by(item_id=item_id).delete()
        
        # Add new partnerships
        partner_ids = request.form.getlist('partner_id')
        partner_shares = request.form.getlist('partner_share')
        
        total_share = 0
        for partner_id, share in zip(partner_ids, partner_shares):
            if partner_id and share:
                partnership = ItemPartner(
                    item_id=item_id,
                    partner_id=int(partner_id),
                    pct_share=float(share)
                )
                db.session.add(partnership)
                total_share += float(share)
        
        # Validate total share
        if total_share > 100:
            flash('Total partner shares cannot exceed 100%.', 'danger')
            db.session.rollback()
        else:
            try:
                db.session.commit()
                flash('Partners updated successfully!', 'success')
                return redirect(url_for('items.index'))
            except Exception as e:
                db.session.rollback()
                flash('Error updating partners. Please try again.', 'danger')
    
    partners = Partner.query.order_by(Partner.name).all()
    return render_template('items/partners.html', item=item, partners=partners)

@items_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_pdf():
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
            
            # Store in session for preview
            import json
            from flask import session
            session['import_preview'] = {
                'auction_id': auction_id,
                'lots': lots
            }
            
            return redirect(url_for('items.import_preview'))
            
        except Exception as e:
            flash(f'Error processing PDF: {str(e)}', 'danger')
            return redirect(request.url)
    
    auctions = Auction.query.order_by(Auction.date.desc()).all()
    return render_template('items/import.html', auctions=auctions)

@items_bp.route('/import/preview', methods=['GET', 'POST'])
@login_required
def import_preview():
    """Preview and confirm PDF import"""
    from flask import session
    
    if 'import_preview' not in session:
        flash('No import data found. Please upload a PDF first.', 'warning')
        return redirect(url_for('items.import_pdf'))
    
    preview_data = session['import_preview']
    
    if request.method == 'POST':
        selected_lots = request.form.getlist('selected_lots')
        
        if not selected_lots:
            flash('Please select at least one lot to import.', 'warning')
            return render_template('items/import_preview.html', 
                                 auction=Auction.query.get(preview_data['auction_id']),
                                 lots=preview_data['lots'])
        
        try:
            imported_count = 0
            for lot_index in selected_lots:
                lot_data = preview_data['lots'][int(lot_index)]
                
                item = Item(
                    auction_id=int(preview_data['auction_id']),
                    lot_number=lot_data.get('lot_number'),
                    title=lot_data.get('title'),
                    description=lot_data.get('description'),
                    planned_max_bid=lot_data.get('planned_max_bid'),
                    target_resale_price=lot_data.get('target_resale_price'),
                    status=ItemStatus.WATCH
                )
                
                db.session.add(item)
                imported_count += 1
            
            db.session.commit()
            
            # Clear session data
            session.pop('import_preview', None)
            
            flash(f'Successfully imported {imported_count} items!', 'success')
            return redirect(url_for('items.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing items: {str(e)}', 'danger')
    
    auction = Auction.query.get(preview_data['auction_id'])
    return render_template('items/import_preview.html', 
                         auction=auction, 
                         lots=preview_data['lots'])

@items_bp.route('/<int:item_id>/update-price', methods=['POST'])
@login_required
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
@login_required
def watchlist():
    """Show watchlist items"""
    items = Item.query.filter_by(status=ItemStatus.WATCH).order_by(Item.created_at.desc()).all()
    return render_template('items/watchlist.html', items=items)

@items_bp.route('/inventory')
@login_required
def inventory():
    """Show inventory (won items)"""
    items = Item.query.filter_by(status=ItemStatus.WON).order_by(Item.updated_at.desc()).all()
    return render_template('items/inventory.html', items=items)

@items_bp.route('/sold')
@login_required
def sold():
    """Show sold items"""
    items = Item.query.filter_by(status=ItemStatus.SOLD).order_by(Item.sale_date.desc()).all()
    return render_template('items/sold.html', items=items)

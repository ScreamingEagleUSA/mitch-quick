from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from replit_auth import require_login
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from models import Item, Auction, Partner, ItemPartner, ItemStatus
from utils.ocr_parser import process_uploaded_pdf
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
@require_login
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
    
    # Get all partners and existing partnerships
    partners = Partner.query.all()
    existing_partnerships = ItemPartner.query.filter_by(item_id=item_id).all()
    
    # Calculate total percentage
    total_percentage = sum(p.pct_share for p in existing_partnerships) if existing_partnerships else 0
    
    return render_template('items/partners.html', 
                         item=item, 
                         partners=partners, 
                         existing_partnerships=existing_partnerships,
                         total_percentage=total_percentage)

@items_bp.route('/import', methods=['GET', 'POST'])
@require_login
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
@require_login
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

@items_bp.route('/inventory/import', methods=['GET', 'POST'])
@require_login
def import_inventory():
    """Import/update inventory from CSV"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                import csv
                import io
                from decimal import Decimal
                
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                
                updated_count = 0
                created_count = 0
                
                for row in csv_input:
                    # Try to find existing item by ID
                    item = None
                    if row.get('ID') and row['ID'].strip():
                        try:
                            item = Item.query.get(int(row['ID']))
                        except ValueError:
                            pass
                    
                    # If no item found by ID, create new one
                    if not item:
                        item = Item()
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Update item fields
                    if row.get('Title'):
                        item.title = row['Title'].strip()
                    if row.get('Description'):
                        item.description = row['Description'].strip()
                    if row.get('Lot Number'):
                        item.lot_number = row['Lot Number'].strip()
                    
                    # Handle numeric fields
                    if row.get('Purchase Price') and row['Purchase Price'].strip():
                        try:
                            item.purchase_price = Decimal(row['Purchase Price'])
                        except:
                            pass
                    
                    if row.get('Refurb Cost') and row['Refurb Cost'].strip():
                        try:
                            item.refurb_cost = Decimal(row['Refurb Cost'])
                        except:
                            pass
                    
                    if row.get('Target Resale Price') and row['Target Resale Price'].strip():
                        try:
                            item.target_resale_price = Decimal(row['Target Resale Price'])
                        except:
                            pass
                    
                    if row.get('Sale Price') and row['Sale Price'].strip():
                        try:
                            item.sale_price = Decimal(row['Sale Price'])
                        except:
                            pass
                    
                    if row.get('Sale Fees') and row['Sale Fees'].strip():
                        try:
                            item.sale_fees = Decimal(row['Sale Fees'])
                        except:
                            pass
                    
                    if row.get('Shipping Cost') and row['Shipping Cost'].strip():
                        try:
                            item.shipping_cost = Decimal(row['Shipping Cost'])
                        except:
                            pass
                    
                    # Handle status
                    if row.get('Status') and row['Status'].strip():
                        try:
                            item.status = ItemStatus(row['Status'].lower())
                        except ValueError:
                            pass
                    
                    # Handle dates
                    if row.get('List Date') and row['List Date'].strip():
                        try:
                            from datetime import datetime
                            item.list_date = datetime.strptime(row['List Date'], '%Y-%m-%d').date()
                        except:
                            pass
                    
                    if row.get('Sale Date') and row['Sale Date'].strip():
                        try:
                            from datetime import datetime
                            item.sale_date = datetime.strptime(row['Sale Date'], '%Y-%m-%d').date()
                        except:
                            pass
                    
                    if row.get('List Channel'):
                        item.list_channel = row['List Channel'].strip()
                    
                    # Set auction (use first auction if not specified and it's a new item)
                    if not item.auction_id:
                        first_auction = Auction.query.first()
                        if first_auction:
                            item.auction_id = first_auction.id
                    
                    db.session.add(item)
                
                db.session.commit()
                flash(f'Successfully imported {created_count} new items and updated {updated_count} existing items', 'success')
                return redirect(url_for('items.inventory'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error importing CSV: {str(e)}', 'error')
        else:
            flash('Please upload a CSV file', 'error')
    
    return render_template('items/import_inventory.html')

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

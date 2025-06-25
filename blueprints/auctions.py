from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from replit_auth import require_login
from datetime import datetime
from models import Auction, Item
from app import db

auctions_bp = Blueprint('auctions', __name__)

@auctions_bp.route('/')
@login_required
def index():
    """List all auctions"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    auctions = Auction.query.order_by(Auction.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('auctions/index.html', auctions=auctions)

@auctions_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new auction"""
    if request.method == 'POST':
        title = request.form.get('title')
        date_str = request.form.get('date')
        location = request.form.get('location')
        url = request.form.get('url')
        notes = request.form.get('notes')
        
        # Validation
        if not title or not date_str:
            flash('Title and date are required.', 'danger')
            return render_template('auctions/form.html')
        
        try:
            auction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('auctions/form.html')
        
        # Create auction
        auction = Auction(
            title=title,
            date=auction_date,
            location=location,
            url=url,
            notes=notes
        )
        
        try:
            db.session.add(auction)
            db.session.commit()
            flash('Auction created successfully!', 'success')
            return redirect(url_for('auctions.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating auction. Please try again.', 'danger')
    
    return render_template('auctions/form.html')

@auctions_bp.route('/<int:auction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(auction_id):
    """Edit auction"""
    auction = Auction.query.get_or_404(auction_id)
    
    if request.method == 'POST':
        auction.title = request.form.get('title')
        date_str = request.form.get('date')
        auction.location = request.form.get('location')
        auction.url = request.form.get('url')
        auction.notes = request.form.get('notes')
        
        # Validation
        if not auction.title or not date_str:
            flash('Title and date are required.', 'danger')
            return render_template('auctions/form.html', auction=auction)
        
        try:
            auction.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('auctions/form.html', auction=auction)
        
        try:
            auction.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Auction updated successfully!', 'success')
            return redirect(url_for('auctions.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating auction. Please try again.', 'danger')
    
    return render_template('auctions/form.html', auction=auction)

@auctions_bp.route('/<int:auction_id>/delete', methods=['POST'])
@login_required
def delete(auction_id):
    """Delete auction"""
    auction = Auction.query.get_or_404(auction_id)
    
    # Check if auction has items
    if auction.items:
        flash('Cannot delete auction with items. Delete items first.', 'danger')
        return redirect(url_for('auctions.index'))
    
    try:
        db.session.delete(auction)
        db.session.commit()
        flash('Auction deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting auction. Please try again.', 'danger')
    
    return redirect(url_for('auctions.index'))

@auctions_bp.route('/<int:auction_id>/view')
@login_required
def view(auction_id):
    """View auction details with items"""
    auction = Auction.query.get_or_404(auction_id)
    
    # Get items for this auction
    items = Item.query.filter_by(auction_id=auction_id).order_by(Item.lot_number).all()
    
    return render_template('auctions/view.html', auction=auction, items=items)

@auctions_bp.route('/api/search')
@login_required
def api_search():
    """API endpoint for auction search (for HTMX)"""
    query = request.args.get('q', '').strip()
    
    if not query:
        auctions = Auction.query.order_by(Auction.date.desc()).limit(10).all()
    else:
        auctions = Auction.query.filter(
            Auction.title.contains(query) | 
            Auction.location.contains(query)
        ).order_by(Auction.date.desc()).limit(10).all()
    
    results = []
    for auction in auctions:
        results.append({
            'id': auction.id,
            'title': auction.title,
            'date': auction.date.strftime('%Y-%m-%d'),
            'location': auction.location or 'N/A'
        })
    
    return jsonify(results)

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from supabase_auth import require_login
from datetime import datetime, date
from models import Item, ItemExpense, ItemStatus
from app import db

expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/')
@require_login
def index():
    """List all expenses"""
    page = request.args.get('page', 1, type=int)
    item_filter = request.args.get('item', 'all')
    category_filter = request.args.get('category', 'all')
    per_page = 20
    
    query = ItemExpense.query
    
    # Apply filters
    if item_filter != 'all':
        query = query.filter(ItemExpense.item_id == int(item_filter))
    
    if category_filter != 'all':
        query = query.filter(ItemExpense.category == category_filter)
    
    expenses = query.order_by(ItemExpense.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    # Get items and categories for filter dropdowns
    items = Item.query.order_by(Item.title).all()
    categories = db.session.query(ItemExpense.category).distinct().filter(
        ItemExpense.category.isnot(None)).all()
    categories = [cat[0] for cat in categories]
    
    # Calculate summary statistics for all expenses (ignoring filters for summary)
    total_expenses = float(db.session.query(db.func.sum(ItemExpense.amount)).scalar() or 0)
    expense_count = ItemExpense.query.count()
    avg_expense = total_expenses / expense_count if expense_count > 0 else 0
    
    # Get latest expense date
    latest_expense = ItemExpense.query.order_by(ItemExpense.date.desc()).first()
    latest_date = latest_expense.date if latest_expense else None
    
    return render_template('expenses/index.html', 
                         expenses=expenses, 
                         items=items,
                         categories=categories,
                         item_filter=item_filter,
                         category_filter=category_filter,
                         total_expenses=total_expenses,
                         expense_count=expense_count,
                         avg_expense=avg_expense,
                         latest_date=latest_date)

@expenses_bp.route('/create', methods=['GET', 'POST'])
@require_login
def create():
    """Create new expense"""
    # Get item_id from query parameter if provided
    item_id = request.args.get('item_id', type=int)
    
    if request.method == 'POST':
        try:
            expense = ItemExpense(
                item_id=int(request.form['item_id']),
                description=request.form['description'],
                amount=float(request.form['amount']),
                date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
                category=request.form.get('category', ''),
                notes=request.form.get('notes', '')
            )
            
            db.session.add(expense)
            db.session.commit()
            
            flash('Expense added successfully!', 'success')
            return redirect(url_for('expenses.index'))
            
        except Exception as e:
            flash(f'Error creating expense: {str(e)}', 'danger')
            return redirect(request.url)
    
    items = Item.query.order_by(Item.title).all()
    return render_template('expenses/form.html', items=items, selected_item_id=item_id)

@expenses_bp.route('/<int:expense_id>/edit', methods=['GET', 'POST'])
@require_login
def edit(expense_id):
    """Edit expense"""
    expense = ItemExpense.query.get_or_404(expense_id)
    
    if request.method == 'POST':
        try:
            expense.item_id = int(request.form['item_id'])
            expense.description = request.form['description']
            expense.amount = float(request.form['amount'])
            expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            expense.category = request.form.get('category', '')
            expense.notes = request.form.get('notes', '')
            expense.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Expense updated successfully!', 'success')
            return redirect(url_for('expenses.index'))
            
        except Exception as e:
            flash(f'Error updating expense: {str(e)}', 'danger')
            return redirect(request.url)
    
    items = Item.query.order_by(Item.title).all()
    return render_template('expenses/form.html', expense=expense, items=items)

@expenses_bp.route('/<int:expense_id>/delete', methods=['POST'])
@require_login
def delete(expense_id):
    """Delete expense"""
    expense = ItemExpense.query.get_or_404(expense_id)
    
    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting expense: {str(e)}', 'danger')
    
    return redirect(url_for('expenses.index'))

@expenses_bp.route('/item/<int:item_id>')
@require_login
def by_item(item_id):
    """Show expenses for specific item"""
    item = Item.query.get_or_404(item_id)
    expenses = ItemExpense.query.filter_by(item_id=item_id).order_by(ItemExpense.date.desc()).all()
    
    return render_template('expenses/by_item.html', item=item, expenses=expenses)
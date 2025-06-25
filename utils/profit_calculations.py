"""
Profit calculation utilities for auction flipping business
"""
from typing import Optional, Dict, Any
from decimal import Decimal, ROUND_HALF_UP

def calculate_gross_profit(sale_price: Optional[float], purchase_price: Optional[float], 
                          refurb_cost: Optional[float] = 0) -> Optional[float]:
    """
    Calculate gross profit = sale_price - purchase_price - refurb_cost
    
    Args:
        sale_price: Final sale price of the item
        purchase_price: Initial purchase price at auction
        refurb_cost: Cost of refurbishment/repairs
    
    Returns:
        Gross profit or None if required data is missing
    """
    if sale_price is None or purchase_price is None:
        return None
    
    refurb_cost = refurb_cost or 0
    return float(sale_price) - float(purchase_price) - float(refurb_cost)

def calculate_net_profit(sale_price: Optional[float], purchase_price: Optional[float],
                        refurb_cost: Optional[float] = 0, sale_fees: Optional[float] = 0,
                        shipping_cost: Optional[float] = 0) -> Optional[float]:
    """
    Calculate net profit = gross_profit - sale_fees - shipping_cost
    
    Args:
        sale_price: Final sale price of the item
        purchase_price: Initial purchase price at auction
        refurb_cost: Cost of refurbishment/repairs
        sale_fees: Marketplace fees (eBay, PayPal, etc.)
        shipping_cost: Shipping and handling costs
    
    Returns:
        Net profit or None if required data is missing
    """
    gross_profit = calculate_gross_profit(sale_price, purchase_price, refurb_cost)
    if gross_profit is None:
        return None
    
    sale_fees = sale_fees or 0
    shipping_cost = shipping_cost or 0
    
    return gross_profit - float(sale_fees) - float(shipping_cost)

def calculate_roi_percentage(sale_price: Optional[float], purchase_price: Optional[float],
                            refurb_cost: Optional[float] = 0, sale_fees: Optional[float] = 0,
                            shipping_cost: Optional[float] = 0) -> Optional[float]:
    """
    Calculate ROI percentage = (net_profit / total_investment) * 100
    
    Args:
        sale_price: Final sale price of the item
        purchase_price: Initial purchase price at auction
        refurb_cost: Cost of refurbishment/repairs
        sale_fees: Marketplace fees
        shipping_cost: Shipping costs
    
    Returns:
        ROI percentage or None if required data is missing or investment is zero
    """
    net_profit = calculate_net_profit(sale_price, purchase_price, refurb_cost, sale_fees, shipping_cost)
    if net_profit is None or purchase_price is None:
        return None
    
    total_investment = float(purchase_price) + float(refurb_cost or 0)
    if total_investment <= 0:
        return None
    
    return (net_profit / total_investment) * 100

def calculate_break_even_price(purchase_price: Optional[float], refurb_cost: Optional[float] = 0,
                              sale_fees_rate: float = 0.10, shipping_cost: Optional[float] = 0) -> Optional[float]:
    """
    Calculate the minimum sale price needed to break even
    
    Args:
        purchase_price: Initial purchase price at auction
        refurb_cost: Cost of refurbishment/repairs
        sale_fees_rate: Marketplace fee rate (e.g., 0.10 for 10%)
        shipping_cost: Fixed shipping costs
    
    Returns:
        Break-even sale price or None if required data is missing
    """
    if purchase_price is None:
        return None
    
    refurb_cost = refurb_cost or 0
    shipping_cost = shipping_cost or 0
    
    # Break-even formula: sale_price = (purchase_price + refurb_cost + shipping_cost) / (1 - fee_rate)
    total_costs = float(purchase_price) + float(refurb_cost) + float(shipping_cost)
    
    if sale_fees_rate >= 1.0:  # Prevent division by zero or negative
        return None
    
    break_even = total_costs / (1 - sale_fees_rate)
    return round(break_even, 2)

def calculate_partner_share(net_profit: Optional[float], percentage_share: float) -> Optional[float]:
    """
    Calculate a partner's share of the profit
    
    Args:
        net_profit: Total net profit from the item
        percentage_share: Partner's percentage share (0-100)
    
    Returns:
        Partner's profit share or None if net profit is None
    """
    if net_profit is None:
        return None
    
    if percentage_share < 0 or percentage_share > 100:
        raise ValueError("Percentage share must be between 0 and 100")
    
    return (float(percentage_share) / 100) * net_profit

def get_item_profit_summary(item) -> Dict[str, Any]:
    """
    Get comprehensive profit summary for an item
    
    Args:
        item: Item model instance
    
    Returns:
        Dictionary with all profit calculations
    """
    summary = {
        'purchase_price': float(item.purchase_price) if item.purchase_price else None,
        'sale_price': float(item.sale_price) if item.sale_price else None,
        'refurb_cost': float(item.refurb_cost) if item.refurb_cost else 0,
        'sale_fees': float(item.sale_fees) if item.sale_fees else 0,
        'shipping_cost': float(item.shipping_cost) if item.shipping_cost else 0,
        'gross_profit': None,
        'net_profit': None,
        'roi_percentage': None,
        'break_even_price': None,
        'total_investment': None
    }
    
    # Calculate profits
    if item.purchase_price:
        summary['total_investment'] = float(item.purchase_price) + (float(item.refurb_cost) if item.refurb_cost else 0)
        
        summary['break_even_price'] = calculate_break_even_price(
            float(item.purchase_price),
            float(item.refurb_cost) if item.refurb_cost else 0,
            0.10,  # Assume 10% marketplace fees
            float(item.shipping_cost) if item.shipping_cost else 0
        )
    
    if item.sale_price and item.purchase_price:
        summary['gross_profit'] = calculate_gross_profit(
            float(item.sale_price),
            float(item.purchase_price),
            float(item.refurb_cost) if item.refurb_cost else 0
        )
        
        summary['net_profit'] = calculate_net_profit(
            float(item.sale_price),
            float(item.purchase_price),
            float(item.refurb_cost) if item.refurb_cost else 0,
            float(item.sale_fees) if item.sale_fees else 0,
            float(item.shipping_cost) if item.shipping_cost else 0
        )
        
        summary['roi_percentage'] = calculate_roi_percentage(
            float(item.sale_price),
            float(item.purchase_price),
            float(item.refurb_cost) if item.refurb_cost else 0,
            float(item.sale_fees) if item.sale_fees else 0,
            float(item.shipping_cost) if item.shipping_cost else 0
        )
    
    return summary

def calculate_portfolio_metrics(items) -> Dict[str, Any]:
    """
    Calculate portfolio-wide metrics
    
    Args:
        items: List of Item model instances
    
    Returns:
        Dictionary with portfolio metrics
    """
    metrics = {
        'total_items': len(items),
        'total_invested': 0,
        'total_sold_value': 0,
        'total_gross_profit': 0,
        'total_net_profit': 0,
        'average_roi': 0,
        'items_sold': 0,
        'items_in_inventory': 0,
        'items_listed': 0,
        'items_watchlist': 0
    }
    
    from models import ItemStatus
    
    profitable_items = []
    
    for item in items:
        # Count by status
        if item.status == ItemStatus.SOLD:
            metrics['items_sold'] += 1
        elif item.status == ItemStatus.WON:
            metrics['items_in_inventory'] += 1
        elif item.status == ItemStatus.LISTED:
            metrics['items_listed'] += 1
        elif item.status == ItemStatus.WATCH:
            metrics['items_watchlist'] += 1
        
        # Calculate investments
        if item.purchase_price:
            investment = float(item.purchase_price) + (float(item.refurb_cost) if item.refurb_cost else 0)
            metrics['total_invested'] += investment
        
        # Calculate profits for sold items
        if item.status == ItemStatus.SOLD and item.sale_price and item.purchase_price:
            metrics['total_sold_value'] += float(item.sale_price)
            
            gross_profit = calculate_gross_profit(
                float(item.sale_price),
                float(item.purchase_price),
                float(item.refurb_cost) if item.refurb_cost else 0
            )
            
            net_profit = calculate_net_profit(
                float(item.sale_price),
                float(item.purchase_price),
                float(item.refurb_cost) if item.refurb_cost else 0,
                float(item.sale_fees) if item.sale_fees else 0,
                float(item.shipping_cost) if item.shipping_cost else 0
            )
            
            roi = calculate_roi_percentage(
                float(item.sale_price),
                float(item.purchase_price),
                float(item.refurb_cost) if item.refurb_cost else 0,
                float(item.sale_fees) if item.sale_fees else 0,
                float(item.shipping_cost) if item.shipping_cost else 0
            )
            
            if gross_profit is not None:
                metrics['total_gross_profit'] += gross_profit
            if net_profit is not None:
                metrics['total_net_profit'] += net_profit
            if roi is not None:
                profitable_items.append(roi)
    
    # Calculate average ROI
    if profitable_items:
        metrics['average_roi'] = sum(profitable_items) / len(profitable_items)
    
    return metrics

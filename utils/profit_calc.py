def calculate_profit_metrics(item):
    """
    Calculate comprehensive profit metrics for an item
    Returns dictionary with all profit calculations
    """
    if not item.purchase_price:
        return {
            'total_cost': 0,
            'gross_profit': 0,
            'net_profit': 0,
            'roi_percentage': 0,
            'break_even_price': 0,
            'profit_margin': 0
        }
    
    purchase_price = float(item.purchase_price)
    refurb_cost = float(item.refurb_cost or 0)
    sale_price = float(item.sale_price or 0)
    sale_fees = float(item.sale_fees or 0)
    shipping_cost = float(item.shipping_cost or 0)
    
    total_cost = purchase_price + refurb_cost
    total_fees = sale_fees + shipping_cost
    
    # Gross profit (before fees)
    gross_profit = sale_price - total_cost if sale_price > 0 else 0
    
    # Net profit (after all costs)
    net_profit = sale_price - total_cost - total_fees if sale_price > 0 else 0
    
    # ROI percentage
    roi_percentage = (net_profit / total_cost) * 100 if total_cost > 0 else 0
    
    # Break-even price (what we need to sell for to break even)
    # Assumes typical marketplace fees of 10%
    typical_fee_rate = 0.10
    break_even_price = total_cost / (1 - typical_fee_rate)
    
    # Profit margin
    profit_margin = (net_profit / sale_price) * 100 if sale_price > 0 else 0
    
    return {
        'total_cost': total_cost,
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'roi_percentage': roi_percentage,
        'break_even_price': break_even_price,
        'profit_margin': profit_margin
    }

def calculate_partner_shares(item):
    """
    Calculate partner share amounts for an item
    Returns list of partner share calculations
    """
    if not item.partners or item.net_profit <= 0:
        return []
    
    partner_shares = []
    net_profit = item.net_profit
    
    for partnership in item.partners:
        share_amount = (float(partnership.pct_share) / 100) * net_profit
        partner_shares.append({
            'partner': partnership.partner,
            'percentage': partnership.pct_share,
            'share_amount': share_amount
        })
    
    return partner_shares

def calculate_portfolio_metrics(items):
    """
    Calculate overall portfolio metrics from a list of items
    """
    total_invested = 0
    total_revenue = 0
    total_fees = 0
    total_net_profit = 0
    sold_count = 0
    won_count = 0
    watch_count = 0
    
    for item in items:
        # Count by status
        if item.status.value == 'sold':
            sold_count += 1
        elif item.status.value == 'won':
            won_count += 1
        elif item.status.value == 'watch':
            watch_count += 1
        
        # Calculate totals
        if item.purchase_price:
            total_invested += item.total_cost
            
        if item.sale_price and item.status.value == 'sold':
            total_revenue += float(item.sale_price)
            total_fees += float(item.sale_fees or 0) + float(item.shipping_cost or 0)
            total_net_profit += item.net_profit
    
    # Calculate metrics
    gross_profit = total_revenue - total_invested
    overall_roi = (total_net_profit / total_invested) * 100 if total_invested > 0 else 0
    average_profit_per_sale = total_net_profit / sold_count if sold_count > 0 else 0
    
    return {
        'total_invested': total_invested,
        'total_revenue': total_revenue,
        'gross_profit': gross_profit,
        'total_net_profit': total_net_profit,
        'overall_roi': overall_roi,
        'average_profit_per_sale': average_profit_per_sale,
        'sold_count': sold_count,
        'won_count': won_count,
        'watch_count': watch_count,
        'total_fees': total_fees
    }

def calculate_break_even_analysis(planned_max_bid, estimated_fees_rate=0.10, refurb_estimate=0):
    """
    Calculate what an item needs to sell for to break even
    given a planned max bid and estimated costs
    """
    total_cost = planned_max_bid + refurb_estimate
    
    # Break-even price accounting for fees
    break_even_price = total_cost / (1 - estimated_fees_rate)
    
    # Add margin targets
    margins = {
        'break_even': break_even_price,
        '20_percent_profit': break_even_price * 1.2,
        '50_percent_profit': break_even_price * 1.5,
        '100_percent_profit': break_even_price * 2.0
    }
    
    return margins

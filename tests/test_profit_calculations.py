"""
Unit tests for profit calculation utilities
"""
import pytest
from decimal import Decimal
from utils.profit_calculations import (
    calculate_gross_profit,
    calculate_net_profit,
    calculate_roi_percentage,
    calculate_break_even_price,
    calculate_partner_share,
    get_item_profit_summary,
    calculate_portfolio_metrics
)
from models import Item, ItemStatus, ItemPartner, Partner, Auction
from datetime import datetime, date


class TestProfitCalculations:
    """Test profit calculation functions"""

    def test_calculate_gross_profit_basic(self):
        """Test basic gross profit calculation"""
        assert calculate_gross_profit(100.0, 50.0) == 50.0
        assert calculate_gross_profit(100.0, 50.0, 10.0) == 40.0
        assert calculate_gross_profit(50.0, 100.0) == -50.0

    def test_calculate_gross_profit_none_values(self):
        """Test gross profit with None values"""
        assert calculate_gross_profit(None, 50.0) is None
        assert calculate_gross_profit(100.0, None) is None
        assert calculate_gross_profit(100.0, 50.0, None) == 50.0

    def test_calculate_gross_profit_zero_values(self):
        """Test gross profit with zero values"""
        assert calculate_gross_profit(0.0, 0.0) == 0.0
        assert calculate_gross_profit(100.0, 0.0) == 100.0
        assert calculate_gross_profit(0.0, 50.0) == -50.0

    def test_calculate_net_profit_basic(self):
        """Test basic net profit calculation"""
        assert calculate_net_profit(100.0, 50.0, 10.0, 5.0, 3.0) == 32.0
        assert calculate_net_profit(100.0, 60.0) == 40.0

    def test_calculate_net_profit_negative(self):
        """Test net profit with loss scenario"""
        assert calculate_net_profit(50.0, 100.0, 10.0, 5.0, 3.0) == -68.0

    def test_calculate_net_profit_none_values(self):
        """Test net profit with None values"""
        assert calculate_net_profit(None, 50.0) is None
        assert calculate_net_profit(100.0, None) is None

    def test_calculate_roi_percentage_basic(self):
        """Test basic ROI calculation"""
        # 100% ROI: $100 sale, $50 investment = $50 profit = 100% ROI
        roi = calculate_roi_percentage(100.0, 50.0)
        assert roi == 100.0

        # 50% ROI: $150 sale, $100 investment = $50 profit = 50% ROI
        roi = calculate_roi_percentage(150.0, 100.0)
        assert roi == 50.0

    def test_calculate_roi_percentage_with_costs(self):
        """Test ROI with additional costs"""
        # Sale: $200, Purchase: $100, Refurb: $20, Fees: $15, Shipping: $5
        # Net profit: $200 - $100 - $20 - $15 - $5 = $60
        # Investment: $100 + $20 = $120
        # ROI: $60 / $120 = 50%
        roi = calculate_roi_percentage(200.0, 100.0, 20.0, 15.0, 5.0)
        assert roi == 50.0

    def test_calculate_roi_percentage_negative(self):
        """Test ROI with loss"""
        roi = calculate_roi_percentage(50.0, 100.0)
        assert roi == -50.0

    def test_calculate_roi_percentage_zero_investment(self):
        """Test ROI with zero investment"""
        assert calculate_roi_percentage(100.0, 0.0) is None

    def test_calculate_roi_percentage_none_values(self):
        """Test ROI with None values"""
        assert calculate_roi_percentage(None, 50.0) is None
        assert calculate_roi_percentage(100.0, None) is None

    def test_calculate_break_even_price_basic(self):
        """Test basic break-even calculation"""
        # Purchase: $100, Fee rate: 10%
        # Break-even = $100 / (1 - 0.10) = $111.11
        break_even = calculate_break_even_price(100.0, 0.0, 0.10, 0.0)
        assert abs(break_even - 111.11) < 0.01

    def test_calculate_break_even_price_with_costs(self):
        """Test break-even with additional costs"""
        # Purchase: $100, Refurb: $20, Shipping: $10, Fee rate: 10%
        # Total costs: $130, Break-even = $130 / 0.9 = $144.44
        break_even = calculate_break_even_price(100.0, 20.0, 0.10, 10.0)
        assert abs(break_even - 144.44) < 0.01

    def test_calculate_break_even_price_high_fee_rate(self):
        """Test break-even with high fee rate"""
        assert calculate_break_even_price(100.0, 0.0, 1.0, 0.0) is None
        assert calculate_break_even_price(100.0, 0.0, 1.5, 0.0) is None

    def test_calculate_break_even_price_none_values(self):
        """Test break-even with None values"""
        assert calculate_break_even_price(None) is None

    def test_calculate_partner_share_basic(self):
        """Test basic partner share calculation"""
        assert calculate_partner_share(100.0, 50.0) == 50.0
        assert calculate_partner_share(100.0, 25.0) == 25.0
        assert calculate_partner_share(100.0, 0.0) == 0.0

    def test_calculate_partner_share_negative_profit(self):
        """Test partner share with negative profit"""
        assert calculate_partner_share(-100.0, 50.0) == -50.0

    def test_calculate_partner_share_invalid_percentage(self):
        """Test partner share with invalid percentages"""
        with pytest.raises(ValueError):
            calculate_partner_share(100.0, -10.0)
        
        with pytest.raises(ValueError):
            calculate_partner_share(100.0, 150.0)

    def test_calculate_partner_share_none_profit(self):
        """Test partner share with None profit"""
        assert calculate_partner_share(None, 50.0) is None


class TestItemProfitSummary:
    """Test item profit summary function"""

    def create_mock_item(self, **kwargs):
        """Create a mock item for testing"""
        class MockItem:
            def __init__(self, **attributes):
                self.purchase_price = attributes.get('purchase_price')
                self.sale_price = attributes.get('sale_price')
                self.refurb_cost = attributes.get('refurb_cost')
                self.sale_fees = attributes.get('sale_fees')
                self.shipping_cost = attributes.get('shipping_cost')
        
        return MockItem(**kwargs)

    def test_get_item_profit_summary_sold_item(self):
        """Test profit summary for sold item"""
        item = self.create_mock_item(
            purchase_price=100.0,
            sale_price=150.0,
            refurb_cost=10.0,
            sale_fees=15.0,
            shipping_cost=5.0
        )
        
        summary = get_item_profit_summary(item)
        
        assert summary['purchase_price'] == 100.0
        assert summary['sale_price'] == 150.0
        assert summary['refurb_cost'] == 10.0
        assert summary['sale_fees'] == 15.0
        assert summary['shipping_cost'] == 5.0
        assert summary['total_investment'] == 110.0
        assert summary['gross_profit'] == 40.0
        assert summary['net_profit'] == 20.0
        assert abs(summary['roi_percentage'] - 18.18) < 0.01

    def test_get_item_profit_summary_incomplete_data(self):
        """Test profit summary with incomplete data"""
        item = self.create_mock_item(purchase_price=100.0)
        
        summary = get_item_profit_summary(item)
        
        assert summary['purchase_price'] == 100.0
        assert summary['sale_price'] is None
        assert summary['gross_profit'] is None
        assert summary['net_profit'] is None
        assert summary['roi_percentage'] is None
        assert summary['total_investment'] == 100.0

    def test_get_item_profit_summary_no_purchase_price(self):
        """Test profit summary with no purchase price"""
        item = self.create_mock_item(sale_price=150.0)
        
        summary = get_item_profit_summary(item)
        
        assert summary['purchase_price'] is None
        assert summary['total_investment'] is None
        assert summary['break_even_price'] is None


class TestPortfolioMetrics:
    """Test portfolio metrics calculation"""

    def create_mock_items(self):
        """Create mock items for portfolio testing"""
        class MockItem:
            def __init__(self, status, purchase_price=None, sale_price=None, refurb_cost=None, 
                        sale_fees=None, shipping_cost=None):
                self.status = status
                self.purchase_price = purchase_price
                self.sale_price = sale_price
                self.refurb_cost = refurb_cost
                self.sale_fees = sale_fees
                self.shipping_cost = shipping_cost
                
                # Calculate properties
                if sale_price and purchase_price:
                    self.net_profit = sale_price - purchase_price - (refurb_cost or 0) - (sale_fees or 0) - (shipping_cost or 0)
                    if purchase_price > 0:
                        total_investment = purchase_price + (refurb_cost or 0)
                        self.roi_percentage = (self.net_profit / total_investment) * 100
                    else:
                        self.roi_percentage = None
                else:
                    self.net_profit = None
                    self.roi_percentage = None

        return [
            MockItem(ItemStatus.SOLD, 100.0, 150.0, 10.0, 15.0, 5.0),  # Net: 20, ROI: 18.18%
            MockItem(ItemStatus.SOLD, 200.0, 250.0, 20.0, 25.0, 10.0), # Net: -5, ROI: -2.27%
            MockItem(ItemStatus.WON, 50.0),
            MockItem(ItemStatus.LISTED, 75.0),
            MockItem(ItemStatus.WATCH),
        ]

    def test_calculate_portfolio_metrics_basic(self):
        """Test basic portfolio metrics calculation"""
        items = self.create_mock_items()
        metrics = calculate_portfolio_metrics(items)
        
        assert metrics['total_items'] == 5
        assert metrics['items_sold'] == 2
        assert metrics['items_in_inventory'] == 1
        assert metrics['items_listed'] == 1
        assert metrics['items_watchlist'] == 1
        
        assert metrics['total_invested'] == 455.0  # 100+10 + 200+20 + 50 + 75
        assert metrics['total_sold_value'] == 400.0  # 150 + 250
        assert metrics['total_net_profit'] == 15.0  # 20 + (-5)
        assert abs(metrics['average_roi'] - 7.95) < 0.01  # Average of 18.18 and -2.27

    def test_calculate_portfolio_metrics_empty(self):
        """Test portfolio metrics with empty list"""
        metrics = calculate_portfolio_metrics([])
        
        assert metrics['total_items'] == 0
        assert metrics['total_invested'] == 0
        assert metrics['total_net_profit'] == 0
        assert metrics['average_roi'] == 0

    def test_calculate_portfolio_metrics_no_sales(self):
        """Test portfolio metrics with no sold items"""
        class MockItem:
            def __init__(self, status, purchase_price=None):
                self.status = status
                self.purchase_price = purchase_price
                self.net_profit = None
                self.roi_percentage = None

        items = [
            MockItem(ItemStatus.WATCH),
            MockItem(ItemStatus.WON, 100.0),
        ]
        
        metrics = calculate_portfolio_metrics(items)
        
        assert metrics['items_sold'] == 0
        assert metrics['total_sold_value'] == 0
        assert metrics['total_net_profit'] == 0
        assert metrics['average_roi'] == 0


class TestProfitCalculationEdgeCases:
    """Test edge cases and error conditions"""

    def test_decimal_precision(self):
        """Test calculations with high precision decimals"""
        # Test with values that might cause floating point issues
        result = calculate_net_profit(33.33, 11.11, 2.22, 1.11, 0.55)
        expected = 33.33 - 11.11 - 2.22 - 1.11 - 0.55
        assert abs(result - expected) < 0.01

    def test_very_large_numbers(self):
        """Test calculations with very large numbers"""
        result = calculate_gross_profit(1000000.0, 500000.0, 100000.0)
        assert result == 400000.0

    def test_very_small_numbers(self):
        """Test calculations with very small numbers"""
        result = calculate_net_profit(1.01, 1.00, 0.005, 0.003, 0.001)
        assert abs(result - 0.001) < 0.0001

    def test_string_to_float_conversion(self):
        """Test that functions handle string inputs gracefully"""
        # These should work as the functions convert to float
        assert calculate_gross_profit("100.50", "50.25") == 50.25

    def test_negative_costs(self):
        """Test behavior with negative costs (edge case)"""
        # Negative refurb cost might represent a rebate or discount
        result = calculate_gross_profit(100.0, 50.0, -10.0)
        assert result == 60.0

    def test_roi_with_zero_profit(self):
        """Test ROI calculation when profit is exactly zero"""
        roi = calculate_roi_percentage(100.0, 100.0)
        assert roi == 0.0


if __name__ == '__main__':
    pytest.main([__file__])

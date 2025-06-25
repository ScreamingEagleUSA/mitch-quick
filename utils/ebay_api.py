import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import os
from app import db

logger = logging.getLogger(__name__)

class EBayAPI:
    """eBay Browse API integration for price suggestions"""
    
    def __init__(self):
        self.app_id = os.environ.get('EBAY_APP_ID', 'default_app_id')
        self.cert_id = os.environ.get('EBAY_CERT_ID', 'default_cert_id')
        self.dev_id = os.environ.get('EBAY_DEV_ID', 'default_dev_id')
        self.base_url = 'https://api.ebay.com'
        self.access_token = None
        self.token_expires = None
        self.cache = {}  # Simple in-memory cache for 24 hours
    
    def get_access_token(self) -> Optional[str]:
        """Get OAuth access token for eBay API"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        try:
            url = f"{self.base_url}/identity/v1/oauth2/token"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {self._get_basic_auth()}'
            }
            data = {
                'grant_type': 'client_credentials',
                'scope': 'https://api.ebay.com/oauth/api_scope'
            }
            
            response = requests.post(url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 7200)  # Default 2 hours
                self.token_expires = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
                return self.access_token
            else:
                logger.error(f"Failed to get eBay access token: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting eBay access token: {e}")
            return None
    
    def _get_basic_auth(self) -> str:
        """Generate basic auth string for eBay OAuth"""
        import base64
        credentials = f"{self.app_id}:{self.cert_id}"
        return base64.b64encode(credentials.encode()).decode()
    
    def get_median_sold_price(self, query: str, condition: str = 'used') -> Optional[float]:
        """Get median sold price for a search query with 24-hour caching"""
        
        # Check cache first
        cache_key = f"{query}_{condition}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(hours=24):
                logger.info(f"Returning cached price for: {query}")
                return cached_data['price']
        
        try:
            access_token = self.get_access_token()
            if not access_token:
                logger.error("Could not get eBay access token")
                return None
            
            # Search for sold listings
            url = f"{self.base_url}/buy/browse/v1/item_summary/search"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
            }
            
            params = {
                'q': query,
                'filter': f'buyingOptions:{{"AUCTION","FIXED_PRICE"}},deliveryCountry:US,conditionIds:{{{self._get_condition_id(condition)}}},itemLocationCountry:US',
                'sort': 'price',
                'limit': 50  # Get more results for better median calculation
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('itemSummaries', [])
                
                if not items:
                    logger.warning(f"No items found for query: {query}")
                    return None
                
                # Extract prices and calculate median
                prices = []
                for item in items:
                    price_info = item.get('price', {})
                    if price_info and price_info.get('value'):
                        try:
                            price = float(price_info['value'])
                            prices.append(price)
                        except (ValueError, TypeError):
                            continue
                
                if not prices:
                    logger.warning(f"No valid prices found for query: {query}")
                    return None
                
                # Calculate median
                prices.sort()
                n = len(prices)
                median_price = prices[n // 2] if n % 2 == 1 else (prices[n // 2 - 1] + prices[n // 2]) / 2
                
                # Cache the result
                self.cache[cache_key] = {
                    'price': median_price,
                    'timestamp': datetime.now()
                }
                
                logger.info(f"Found median price ${median_price:.2f} for query: {query}")
                return median_price
                
            else:
                logger.error(f"eBay API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting eBay price data: {e}")
            return None
    
    def _get_condition_id(self, condition: str) -> str:
        """Map condition string to eBay condition ID"""
        condition_map = {
            'new': '1000',
            'like_new': '1500',
            'excellent': '2000',
            'very_good': '2500',
            'good': '3000',
            'used': '3000',
            'acceptable': '4000',
            'for_parts': '7000'
        }
        return condition_map.get(condition.lower(), '3000')  # Default to 'used'
    
    def update_item_price_suggestion(self, item):
        """Update an item's eBay price suggestion"""
        if not item.title:
            return False
        
        try:
            # Create search query from item title
            search_query = item.title[:80]  # Limit query length
            
            # Get price suggestion
            suggested_price = self.get_median_sold_price(search_query)
            
            if suggested_price:
                item.ebay_suggested_price = suggested_price
                item.ebay_price_updated = datetime.utcnow()
                db.session.commit()
                logger.info(f"Updated price suggestion for item {item.id}: ${suggested_price:.2f}")
                return True
            else:
                logger.warning(f"Could not get price suggestion for item {item.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating price suggestion for item {item.id}: {e}")
            return False

# Global instance
ebay_api = EBayAPI()

def get_price_suggestion(query: str, condition: str = 'used') -> Optional[float]:
    """Convenience function to get price suggestion"""
    return ebay_api.get_median_sold_price(query, condition)

def update_all_watchlist_prices():
    """Update price suggestions for all watchlist items"""
    from models import Item, ItemStatus
    
    try:
        watchlist_items = Item.query.filter_by(status=ItemStatus.WATCH).all()
        updated_count = 0
        
        for item in watchlist_items:
            if ebay_api.update_item_price_suggestion(item):
                updated_count += 1
        
        logger.info(f"Updated price suggestions for {updated_count}/{len(watchlist_items)} watchlist items")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error updating watchlist prices: {e}")
        return 0

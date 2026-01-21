"""
OpenInsider scraper module.
Scrapes insider transaction data from OpenInsider.com.
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import hashlib
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import setup_logger
from src.utils.config import config
from src.utils.database import Database

logger = setup_logger('scraper')


class OpenInsiderScraper:
    """
    Scraper for OpenInsider.com to collect insider transaction data.
    """
    
    BASE_URL = "http://openinsider.com/screener"
    
    def __init__(self):
        """Initialize the scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_recent_transactions(self, days: int = None) -> pd.DataFrame:
        """
        Scrape recent insider transactions.
        
        Args:
            days: Number of days to look back (default from config)
        
        Returns:
            DataFrame with insider transaction data
        """
        if days is None:
            days = config.lookback_days
        
        logger.info(f"Scraping insider transactions from last {days} days...")
        
        # OpenInsider URL parameters for filtering
        # Focus on purchases (P) by key insiders
        params = {
            'sortcol': '1',  # Sort by filing date
            'cnt': '100',    # Number of results
            'page': '1',     # Page number
            'x': 'Purchase', # Filter for purchases
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find the main data table
            table = soup.find('table', {'class': 'tinytable'})
            
            if not table:
                logger.warning("No data table found on page")
                return pd.DataFrame()
            
            # Extract table data
            transactions = self._parse_table(table)
            
            # Filter by date
            cutoff_date = datetime.now() - timedelta(days=days)
            transactions = transactions[transactions['filing_date'] >= cutoff_date]
            
            logger.info(f"Scraped {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error scraping OpenInsider: {e}")
            return pd.DataFrame()
    
    def _parse_table(self, table) -> pd.DataFrame:
        """Parse the OpenInsider data table."""
        rows = []
        
        # Skip header row
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            
            if len(cols) < 10:
                continue
            
            try:
                # Extract data from columns
                filing_date_str = cols[1].text.strip()
                trade_date_str = cols[2].text.strip()
                ticker = cols[3].text.strip()
                company_name = cols[4].text.strip()
                insider_name = cols[5].text.strip()
                insider_title = cols[6].text.strip()
                trade_type = cols[7].text.strip()
                price = self._parse_float(cols[8].text.strip())
                shares = self._parse_float(cols[9].text.strip())
                value = self._parse_float(cols[10].text.strip())
                shares_owned = self._parse_float(cols[11].text.strip())
                
                # Parse dates
                filing_date = pd.to_datetime(filing_date_str, format='%Y-%m-%d', errors='coerce')
                trade_date = pd.to_datetime(trade_date_str, format='%Y-%m-%d', errors='coerce')
                
                # Skip if essential data is missing
                if pd.isna(filing_date) or not ticker or not insider_name:
                    continue
                
                # Calculate total value if not provided
                if pd.isna(value) and not pd.isna(shares) and not pd.isna(price):
                    value = shares * price
                
                rows.append({
                    'ticker': ticker,
                    'company_name': company_name,
                    'insider_name': insider_name,
                    'insider_title': insider_title,
                    'transaction_date': trade_date,
                    'filing_date': filing_date,
                    'transaction_type': trade_type,
                    'shares': shares,
                    'price_per_share': price,
                    'total_value': value,
                    'shares_owned_after': shares_owned,
                })
                
            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue
        
        df = pd.DataFrame(rows)
        
        if len(df) > 0:
            # Add data hash for deduplication
            df['data_hash'] = df.apply(self._generate_hash, axis=1)
            df['scraped_at'] = datetime.utcnow()
        
        return df
    
    def _parse_float(self, text: str) -> Optional[float]:
        """Parse a float value from text, handling currency and thousands separators."""
        try:
            # Remove common currency symbols and thousands separators
            text = text.replace('$', '').replace(',', '').replace('£', '').strip()
            if text in ['', '-', 'N/A']:
                return None
            return float(text)
        except (ValueError, AttributeError):
            return None
    
    def _generate_hash(self, row: pd.Series) -> str:
        """Generate a unique hash for a transaction to enable deduplication."""
        # Create a string with key fields
        hash_string = f"{row['ticker']}_{row['insider_name']}_{row['filing_date']}_{row['shares']}_{row['price_per_share']}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def filter_significant_purchases(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter transactions for significant purchases by key insiders.
        
        Args:
            df: DataFrame with all transactions
        
        Returns:
            Filtered DataFrame meeting our criteria
        """
        if df.empty:
            return df
        
        logger.info("Filtering for significant purchases...")
        
        # Filter for purchases only
        df = df[df['transaction_type'].str.upper() == 'P'].copy()
        
        # Filter for key insider titles
        key_titles = ['CEO', 'CFO', 'Chief Executive', 'Chief Financial', 'Director', 
                      'President', 'COO', 'Chief Operating']
        
        title_mask = df['insider_title'].str.contains('|'.join(key_titles), case=False, na=False)
        df = df[title_mask].copy()
        
        # Filter by transaction value
        min_value = config.min_transaction_value
        df = df[df['total_value'] >= min_value].copy()
        
        # Remove transactions with missing critical data
        df = df.dropna(subset=['ticker', 'total_value', 'filing_date'])
        
        logger.info(f"Filtered to {len(df)} significant purchases")
        return df


def main():
    """Main function to run the scraper."""
    logger.info("Starting OpenInsider scraper...")
    
    # Initialize scraper and database
    scraper = OpenInsiderScraper()
    db = Database()
    
    try:
        # Scrape recent transactions
        all_transactions = scraper.scrape_recent_transactions()
        
        if all_transactions.empty:
            logger.warning("No transactions found")
            return
        
        # Filter for significant purchases
        significant = scraper.filter_significant_purchases(all_transactions)
        
        if significant.empty:
            logger.warning("No significant purchases found")
            return
        
        # Save to database
        new_count = 0
        for _, row in significant.iterrows():
            transaction_data = row.to_dict()
            result = db.add_transaction(transaction_data)
            if result:
                new_count += 1
                logger.info(f"New transaction: {row['ticker']} - {row['insider_name']} - ${row['total_value']:,.0f}")
        
        logger.info(f"Saved {new_count} new transactions to database")
        
        # Save raw data to CSV for backup
        output_dir = Path('data/raw')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'insider_transactions_{timestamp}.csv'
        significant.to_csv(output_file, index=False)
        logger.info(f"Saved raw data to {output_file}")
        
    except Exception as e:
        logger.error(f"Error in scraper main: {e}")
        raise
    finally:
        db.close()
    
    logger.info("Scraping completed successfully")


if __name__ == "__main__":
    main()

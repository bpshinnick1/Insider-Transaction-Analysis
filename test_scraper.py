"""
Unit tests for the OpenInsider scraper.
"""

import pytest
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.data_collection.scraper import OpenInsiderScraper
from src.utils.config import config


class TestOpenInsiderScraper:
    """Test cases for OpenInsiderScraper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = OpenInsiderScraper()
    
    def test_scraper_initialization(self):
        """Test that scraper initializes correctly."""
        assert self.scraper is not None
        assert self.scraper.session is not None
    
    def test_parse_float_valid(self):
        """Test parsing valid float strings."""
        assert self.scraper._parse_float("$1,234.56") == 1234.56
        assert self.scraper._parse_float("1234.56") == 1234.56
        assert self.scraper._parse_float("£10,000") == 10000.0
    
    def test_parse_float_invalid(self):
        """Test parsing invalid float strings."""
        assert self.scraper._parse_float("") is None
        assert self.scraper._parse_float("-") is None
        assert self.scraper._parse_float("N/A") is None
    
    def test_generate_hash_consistency(self):
        """Test that hash generation is consistent."""
        row = pd.Series({
            'ticker': 'AAPL',
            'insider_name': 'Tim Cook',
            'filing_date': datetime(2024, 1, 1),
            'shares': 1000,
            'price_per_share': 150.0
        })
        
        hash1 = self.scraper._generate_hash(row)
        hash2 = self.scraper._generate_hash(row)
        
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length
    
    def test_filter_significant_purchases(self):
        """Test filtering logic for significant purchases."""
        # Create test data
        df = pd.DataFrame([
            {
                'ticker': 'AAPL',
                'insider_title': 'CEO',
                'transaction_type': 'P',
                'total_value': 200000,
                'filing_date': datetime.now()
            },
            {
                'ticker': 'MSFT',
                'insider_title': 'Engineer',
                'transaction_type': 'P',
                'total_value': 50000,
                'filing_date': datetime.now()
            },
            {
                'ticker': 'GOOGL',
                'insider_title': 'CFO',
                'transaction_type': 'S',  # Sale, not purchase
                'total_value': 300000,
                'filing_date': datetime.now()
            }
        ])
        
        filtered = self.scraper.filter_significant_purchases(df)
        
        # Should only keep AAPL (CEO purchase over threshold)
        assert len(filtered) == 1
        assert filtered.iloc[0]['ticker'] == 'AAPL'
    
    def test_filter_empty_dataframe(self):
        """Test filtering with empty DataFrame."""
        df = pd.DataFrame()
        result = self.scraper.filter_significant_purchases(df)
        
        assert result.empty


if __name__ == "__main__":
    pytest.main([__file__, '-v'])

"""
Unit tests for the signal generator.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.analysis.signal_generator import SignalGenerator


class TestSignalGenerator:
    """Test cases for SignalGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SignalGenerator()
    
    def test_generator_initialization(self):
        """Test that generator initializes correctly."""
        assert self.generator is not None
        assert self.generator.db is not None
        assert self.generator.price_fetcher is not None
    
    def test_calculate_conviction_high_value(self):
        """Test conviction scoring for high-value transaction."""
        transactions = pd.DataFrame([{
            'id': 1,
            'ticker': 'AAPL',
            'insider_name': 'Tim Cook',
            'insider_title': 'CEO',
            'transaction_date': datetime.now(),
            'filing_date': datetime.now(),
            'total_value': 1000000,
            'shares': 5000,
            'price_per_share': 200
        }])
        
        score = self.generator._calculate_conviction(transactions)
        
        # High value + CEO should give high score
        assert score >= 50
        assert score <= 100
    
    def test_calculate_conviction_multiple_insiders(self):
        """Test conviction scoring with multiple insiders."""
        transactions = pd.DataFrame([
            {
                'id': 1,
                'ticker': 'AAPL',
                'insider_name': 'Tim Cook',
                'insider_title': 'CEO',
                'transaction_date': datetime.now(),
                'filing_date': datetime.now(),
                'total_value': 500000,
                'shares': 2500,
                'price_per_share': 200
            },
            {
                'id': 2,
                'ticker': 'AAPL',
                'insider_name': 'Luca Maestri',
                'insider_title': 'CFO',
                'transaction_date': datetime.now(),
                'filing_date': datetime.now(),
                'total_value': 300000,
                'shares': 1500,
                'price_per_share': 200
            }
        ])
        
        score = self.generator._calculate_conviction(transactions)
        
        # Multiple senior executives should boost score
        assert score >= 60
    
    def test_determine_signal_strength(self):
        """Test signal strength determination."""
        assert self.generator._determine_signal_strength(80) == 'HIGH'
        assert self.generator._determine_signal_strength(60) == 'MEDIUM'
        assert self.generator._determine_signal_strength(40) == 'LOW'
        assert self.generator._determine_signal_strength(20) == 'NONE'
    
    def test_calculate_position_size(self):
        """Test position size calculation."""
        # High conviction
        shares_high = self.generator._calculate_position_size(100, 90)
        
        # Low conviction
        shares_low = self.generator._calculate_position_size(100, 40)
        
        # High conviction should result in more shares
        assert shares_high > shares_low
        
        # Should have minimum shares
        assert shares_high >= 10
        assert shares_low >= 10
    
    def test_generate_signal_notes(self):
        """Test signal notes generation."""
        transactions = pd.DataFrame([
            {
                'ticker': 'AAPL',
                'insider_name': 'Tim Cook',
                'total_value': 500000
            },
            {
                'ticker': 'AAPL',
                'insider_name': 'Luca Maestri',
                'total_value': 300000
            }
        ])
        
        notes = self.generator._generate_signal_notes(transactions)
        
        assert '2 insider purchase' in notes
        assert 'Tim Cook' in notes
        assert 'Luca Maestri' in notes
    
    def teardown_method(self):
        """Clean up after tests."""
        self.generator.close()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])

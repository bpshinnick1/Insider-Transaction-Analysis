"""
Main entry point for the insider trading bot with automated scheduling.
"""

import schedule
import time
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.utils.logger import setup_logger
from src.utils.config import config
from src.data_collection.scraper import OpenInsiderScraper
from src.analysis.signal_generator import SignalGenerator
from src.trading.trader import TradingBot

logger = setup_logger('main')


def run_scraper():
    """Scheduled task to scrape insider data."""
    logger.info("Running scheduled scraper...")
    scraper = OpenInsiderScraper()
    
    try:
        from src.utils.database import Database
        db = Database()
        
        transactions = scraper.scrape_recent_transactions()
        significant = scraper.filter_significant_purchases(transactions)
        
        new_count = 0
        for _, row in significant.iterrows():
            if db.add_transaction(row.to_dict()):
                new_count += 1
        
        logger.info(f"Scraper found {new_count} new transactions")
        db.close()
        
    except Exception as e:
        logger.error(f"Error in scheduled scraper: {e}")


def run_signal_generator():
    """Scheduled task to generate signals."""
    logger.info("Running scheduled signal generator...")
    generator = SignalGenerator()
    
    try:
        signals = generator.generate_signals()
        logger.info(f"Signal generator created {len(signals)} signals")
    except Exception as e:
        logger.error(f"Error in scheduled signal generator: {e}")
    finally:
        generator.close()


def main():
    """Run the bot with scheduling."""
    logger.info("="*60)
    logger.info("INSIDER TRADING BOT - AUTOMATED MODE")
    logger.info("="*60)
    logger.info(f"Scrape interval: Every {config.scrape_interval_hours} hours")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60 + "\n")
    
    # Schedule tasks
    # Run scraper every N hours
    schedule.every(config.scrape_interval_hours).hours.do(run_scraper)
    
    # Run signal generator 15 minutes after scraper
    # This ensures fresh data is available
    schedule.every(config.scrape_interval_hours).hours.do(run_signal_generator)
    
    # Run initial tasks immediately
    logger.info("Running initial data collection...")
    run_scraper()
    time.sleep(5)
    run_signal_generator()
    
    logger.info("\nScheduled tasks configured. Bot running...\n")
    logger.info("Press Ctrl+C to stop\n")
    
    # Main scheduling loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal")
        logger.info("Stopping bot...")
    
    logger.info("Bot stopped")


if __name__ == "__main__":
    main()

"""
Logging configuration for the trading bot.
Provides structured logging to file and console.
"""

import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = 'trading_bot', log_file: str = None, level: str = None):
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (default from env or logs/trading_bot.log)
        level: Log level (default from env or INFO)
    
    Returns:
        logging.Logger: Configured logger
    """
    # Get configuration from environment
    if log_file is None:
        log_file = os.getenv('LOG_FILE', 'logs/trading_bot.log')
    
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    file_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


# Create default logger
logger = setup_logger()


if __name__ == "__main__":
    # Test logging
    test_logger = setup_logger('test')
    test_logger.debug("Debug message")
    test_logger.info("Info message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
    print(f"\nLog file created at: {os.getenv('LOG_FILE', 'logs/trading_bot.log')}")

"""Logging configuration for digdag graph."""

import logging
import sys
from typing import Optional


def setup_logging(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """Configure structured logging for the application.
    
    Args:
        verbose: Enable debug logging
        quiet: Minimal output (warnings and errors only)
    
    Returns:
        Configured logger instance
    """
    level = logging.WARNING if quiet else (logging.DEBUG if verbose else logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Return application logger
    logger = logging.getLogger('digdaggraph')
    logger.setLevel(level)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (defaults to 'digdaggraph')
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name or 'digdaggraph')

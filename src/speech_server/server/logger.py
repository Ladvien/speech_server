import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with basic configuration."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger

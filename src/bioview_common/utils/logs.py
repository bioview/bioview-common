import contextlib
import os
from functools import wraps
import logging 

def log_print(
    logger: logging.Logger, 
    level: str = 'info',
    message: str = ''
) -> None:
    if logger is not None:
        log_method = getattr(logger, level, None)
        if log_method:
            log_method(message)
    elif level == 'debug':
        print(message)
        

def silence_function(func):
    """A decorator to silence a function that prints to stdout."""
    DEVNULL = open(os.devnull, 'w') # Move all stdout to /dev/null
    
    @wraps(func)

    def wrapper(*args, **kwargs):
        with contextlib.redirect_stdout(DEVNULL):
            return func(*args, **kwargs)
    
    return wrapper
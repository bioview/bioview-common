import logging 

def log_print(
    logger: logging.Logger, 
    level: str = 'info',
    message: str = '', 
    fallback: bool = False
) -> None:
    if logger is not None:
        log_method = getattr(logger, level, None)
        if log_method:
            log_method(message)
    elif fallback:
        print(message)
        
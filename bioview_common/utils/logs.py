import contextlib
import logging
import os
import sys


def log_print(logger: logging.Logger, level: str = "info", message: str = "") -> None:
    if logger is not None:
        log_method = getattr(logger, level, None)
        if log_method:
            log_method(message)
    elif level == "debug":
        print(message)


@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def emit_signal(func, *args, **kwargs):
    if func is None:
        return
    try:
        func(*args, **kwargs)
    except Exception:
        print(f"Unable to emit signal: {repr(func)}")

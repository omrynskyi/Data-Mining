"""
Execution timing utilities for CRISP-DM stages and mining operations.
"""

import functools
import time
from contextlib import contextmanager
from typing import Callable, Generator, Optional


class Timer:
    """High-precision execution timer."""

    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed_seconds: float = 0.0

    def __enter__(self) -> "Timer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self) -> "Timer":
        self.start_time = time.perf_counter()
        self.end_time = None
        return self

    def stop(self) -> float:
        if self.start_time is None:
            raise RuntimeError("Timer was never started.")
        self.end_time = time.perf_counter()
        self.elapsed_seconds = self.end_time - self.start_time
        return self.elapsed_seconds

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_seconds * 1000.0


@contextmanager
def time_block(name: str = "Block") -> Generator[Timer, None, None]:
    """Context manager for timing code blocks."""
    timer = Timer(name=name)
    timer.start()
    try:
        yield timer
    finally:
        timer.stop()


def timed_function(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        return result, duration
    return wrapper

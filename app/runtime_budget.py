"""Bound total inference concurrency, including simultaneous HTTP requests."""
import os
import threading

MODEL_SLOTS = threading.BoundedSemaphore(max(1, min(4, int(os.environ.get('ORCHA_MODEL_WORKERS', '2')))))

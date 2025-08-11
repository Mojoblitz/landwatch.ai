import os
from .config import RAW_DIR, PROCESSED_DIR, MAP_DIR

def ensure_dirs():
    for d in (RAW_DIR, PROCESSED_DIR, MAP_DIR):
        os.makedirs(d, exist_ok=True)
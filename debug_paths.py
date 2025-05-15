# debug_paths.py
from pathlib import Path
import os

print("Starting debug script...")
current_file = Path(__file__)
print(f"Current file: {current_file}")
BASE_DIR = current_file.resolve().parent.parent
print(f"BASE_DIR: {BASE_DIR}")
print(f"Files in BASE_DIR: {os.listdir(BASE_DIR)}")
try:
    env_file = BASE_DIR / '.env'
    print(f".env file exists: {env_file.exists()}")
    if env_file.exists():
        print(f".env file content (first 100 chars): {env_file.read_text()[:100]}")
except Exception as e:
    print(f"Error reading .env: {e}")
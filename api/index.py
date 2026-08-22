import sys
import os

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.schema import init_db
from backend.database.seed import seed_database
from backend.main import app

# Explicitly initialize and seed database for Vercel serverless runtime
try:
    init_db()
    seed_database()
except Exception as e:
    print(f"Vercel DB Init Error: {e}")

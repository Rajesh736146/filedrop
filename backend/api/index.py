import sys
import os

# Add backend directory to path so app module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

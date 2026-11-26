"""Makes `boneage` importable when running pytest from ml/ without an install step."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

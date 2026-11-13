# Lets the tests import files from the main project folder
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

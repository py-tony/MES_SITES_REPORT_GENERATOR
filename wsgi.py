import os
import sys

# Add the project directory to the sys.path
proj_dir = os.path.dirname(__file__)
if proj_dir not in sys.path:
    sys.path.insert(0, proj_dir)

from app import app as application

# For PythonAnywhere, ensure instance folder exists
os.makedirs(os.path.join(proj_dir, 'instance'), exist_ok=True)

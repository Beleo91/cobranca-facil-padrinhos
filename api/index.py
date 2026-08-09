import os
import sys

# Configura diretório raiz
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.main import app as application

# Exposta diretamente para o Vercel Serverless Runner
app = application

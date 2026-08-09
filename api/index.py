import os
import sys

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importa a instância FastAPI
from backend.app.main import app

# Variável exposta para o runner serverless da Vercel
app = app

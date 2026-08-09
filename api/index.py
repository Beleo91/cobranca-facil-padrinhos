import os
import sys

# Adiciona o diretório da raiz ao PATH para que o python encontre o módulo 'backend'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import app
# Exporta app para o runner serverless da Vercel

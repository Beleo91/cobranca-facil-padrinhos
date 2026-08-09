import os
import sys
from fastapi import Request
from fastapi.responses import JSONResponse

# Adiciona o diretório da raiz ao PATH para que o python encontre o módulo 'backend'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import app

@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno no servidor Serverless.",
            "erro": str(exc)
        }
    )

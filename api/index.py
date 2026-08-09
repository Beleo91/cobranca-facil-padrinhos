import os
import sys

# Adiciona diretórios do projeto ao sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

for path in (BASE_DIR, BACKEND_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import Request
from fastapi.responses import JSONResponse

try:
    from backend.app.main import app
except ImportError:
    from app.main import app

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno no servidor Serverless.",
            "erro": str(exc)
        }
    )

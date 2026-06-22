import uvicorn
import os

if __name__ == "__main__":
    print("🚀 Iniciando a Central do Torneio de Truco Cego Unificada...")
    
    # Executa o servidor chamando diretamente o 'app' principal do main.py
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
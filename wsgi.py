import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importar a aplicação Flask
from src.main import app

if __name__ == "__main__":
    app.run()

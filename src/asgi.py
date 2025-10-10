# asgi.py
from src.main import app            # seu app Flask
from asgiref.wsgi import WsgiToAsgi

asgi_app = WsgiToAsgi(app)

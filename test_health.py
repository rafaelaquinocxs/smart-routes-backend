import requests

API_URL = "https://shrouded-brook-92780-0986488286e3.herokuapp.com"

print("Testando health check...")
try:
    response = requests.get(f"{API_URL}/health", timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"ERRO: {e}")

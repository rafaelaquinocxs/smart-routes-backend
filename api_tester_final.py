import requests
import json
import time

API_URL = "https://shrouded-brook-92780-0986488286e3.herokuapp.com/api"

def test_post_container_final():
    print("\n--- Testando POST /containers (Versão Final) ---")
    new_container = {
        "uid": "TESTE_FINAL_001",
        "name": "Container Teste Final",
        "location": "Rua Fictícia, 200",
        "latitude": -23.5505,
        "longitude": -46.6333,
        "container_type": "ORGANICO",
        "dist_empty": 100,
        "dist_full": 10
    }
    try:
        response = requests.post(f"{API_URL}/containers", json=new_container)
        response.raise_for_status()
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Sucesso: {data.get('success')}")
        print(f"Mensagem: {data.get('message')}")
        print(f"Dados do Container Criado: {data.get('data')}")
        return data.get('data')
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao criar container: {e}")
        if 'response' in locals() and response is not None:
             print(f"Detalhes da Resposta de Erro: {response.text}")
        return None

def test_get_containers():
    print("\n--- Testando GET /containers ---")
    try:
        response = requests.get(f"{API_URL}/containers")
        response.raise_for_status()
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Total de Containers: {len(data.get('data', []))}")
        return data.get('data')
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao buscar containers: {e}")
        return None

def test_optimize_route():
    print("\n--- Testando POST /optimize-route ---")
    payload = {"fill_threshold": 50}  # Reduzir o threshold para encontrar containers
    try:
        response = requests.post(f"{API_URL}/optimize-route", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Sucesso: {data.get('success')}")
        print(f"Mensagem: {data.get('message')}")
        if data.get('success'):
            print(f"Distância Total: {data.get('total_distance')} km")
            print(f"Tempo Estimado: {data.get('estimated_time')} min")
            print(f"Containers na Rota: {len(data.get('containers', []))}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao otimizar rota: {e}")
        return None

if __name__ == "__main__":
    print(f"Testando API em: {API_URL}")
    test_get_containers()
    test_post_container_final()
    test_optimize_route()
    print("\n--- Testes da API concluídos ---")

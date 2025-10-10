from flask import Blueprint, request, jsonify
from src.models.container import Container
from src.models.sensor_data import SensorData
from src.models.user import db
import random
from datetime import datetime

simulation_bp = Blueprint("simulation", __name__)

@simulation_bp.route("/simulate-sensor-data", methods=["POST"])
def simulate_sensor_data():
    """Simula dados de sensores para containers"""
    try:
        # Buscar todos os containers ativos
        containers = Container.query.filter_by(ativa=True).all()
        
        if not containers:
            return jsonify({
                "success": False,
                "error": "Nenhum container encontrado"
            }), 404
        
        simulated_data = []
        
        for container in containers:
            # Simular diferentes níveis de enchimento
            # 30% dos containers estarão >75% cheios
            if random.random() < 0.3:
                # Container cheio (75-95%)
                fill_level = random.randint(75, 95)
            else:
                # Container com nível normal (10-70%)
                fill_level = random.randint(10, 70)
            
            # Calcular distância baseada no nível de enchimento
            # Assumindo que max_distance e min_distance ainda são usados para cálculo
            # Se não forem, precisaríamos de uma lógica diferente ou de valores padrão
            max_dist = 100 # Valor padrão se não houver no modelo
            min_dist = 10  # Valor padrão se não houver no modelo
            
            # O modelo Container agora tem 'nivel' e não 'max_distance'/'min_distance'
            # Vamos simular a distância com base no fill_level diretamente
            distance = int(max_dist - (fill_level / 100.0) * (max_dist - min_dist))
            
            # Simular outros dados do sensor
            battery_level = random.randint(20, 100)
            rssi_val = random.randint(-80, -40)
            
            # Criar dados do sensor na tabela mensagens_sensores
            sensor_data = SensorData(
                uid_sensor=container.uid,
                nSeq=random.randint(1, 1000),
                rssi=rssi_val,
                battery_pct=battery_level,
                dist=distance,
                timestamp=int(datetime.utcnow().timestamp()), # Unix timestamp
                fill_level=float(fill_level), # Campo adicional para compatibilidade
                received_at=datetime.utcnow()
            )
            
            db.session.add(sensor_data)
            
            # Atualizar status do container na tabela sensores
            container.nivel = fill_level
            container.ativa = True # Assumir que está ativo se enviando dados
            container.last_updated = datetime.utcnow()
            
            simulated_data.append({
                'uid': container.uid,
                'name': container.nome_amigavel,
                'fill_level': fill_level,
                'distance': distance,
                'battery_level': battery_level,
                'status': container.get_status(fill_level)
            })
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Dados simulados para {len(containers)} containers",
            "data": simulated_data
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@simulation_bp.route("/reset-sensor-data", methods=["POST"])
def reset_sensor_data():
    """Remove todos os dados de sensores simulados e reseta containers"""
    try:
        # Remover todos os dados de sensores da tabela mensagens_sensores
        SensorData.query.delete()
        
        # Resetar status dos containers na tabela sensores
        containers = Container.query.all()
        for container in containers:
            container.ativa = False # Inativar
            container.nivel = 0 # Resetar nível
            container.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Dados de sensores e status de containers resetados"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


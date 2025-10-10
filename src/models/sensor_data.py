from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class SensorData(db.Model):
    __tablename__ = 'mensagens_sensores'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid_sensor = db.Column(db.String(50), db.ForeignKey('sensores.uid'), nullable=True, index=True)
    nSeq = db.Column(db.Integer, nullable=True)
    rssi = db.Column(db.Integer, nullable=True)
    battery_pct = db.Column(db.Integer, nullable=True)
    dist = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.BigInteger, nullable=True) # Armazenar como BigInteger (Unix timestamp)
    
    # Campos adicionais removidos pois não existem na tabela real
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'container_uid': self.uid_sensor,
            'nseq': self.nSeq,
            'rssi': self.rssi,
            'battery_pct': self.battery_pct,
            'distance': self.dist,
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else None
        }
    
    def get_signal_quality(self):
        """
        Retorna a qualidade do sinal baseada no RSSI
        
        Returns:
            str: Qualidade do sinal (Excelente, Bom, Regular, Ruim)
        """
        if self.rssi is None: return 'Desconhecido'
        if self.rssi >= -50:
            return 'Excelente'
        elif self.rssi >= -60:
            return 'Bom'
        elif self.rssi >= -70:
            return 'Regular'
        else:
            return 'Ruim'
    
    def get_battery_status(self):
        """
        Retorna o status da bateria
        
        Returns:
            str: Status da bateria (Alto, Médio, Baixo, Crítico)
        """
        if self.battery_pct is None: return 'Desconhecido'
        if self.battery_pct >= 80:
            return 'Alto'
        elif self.battery_pct >= 50:
            return 'Médio'
        elif self.battery_pct >= 20:
            return 'Baixo'
        else:
            return 'Crítico'
    
    def __repr__(self):
        return f'<SensorData {self.uid_sensor} - {self.timestamp}>'

# A classe Gateway foi removida pois não há uma tabela correspondente no novo esquema SQL.
# A lógica que dependia de Gateway precisará ser adaptada no mqtt_service.py


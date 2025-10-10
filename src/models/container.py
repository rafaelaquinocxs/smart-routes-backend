from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Container(db.Model):
    __tablename__ = 'sensores'
    
    uid = db.Column(db.String(50), primary_key=True) # uid é a chave primária
    nome_amigavel = db.Column(db.String(100), nullable=False)
    coordenada_x = db.Column(db.Numeric(10,6), nullable=False)
    coordenada_y = db.Column(db.Numeric(10,6), nullable=False)
    ativa = db.Column(db.Boolean, nullable=False)
    nivel = db.Column(db.Integer, nullable=False) # Nível de preenchimento (0-100)
    
    # Adicionar campos para compatibilidade com o sistema existente, se necessário
    # Estes campos não estão no SQL, mas podem ser úteis para o backend
    # status = db.Column(db.String(50), default='active') # Status calculado (Cheio, Alto, etc.)
    # last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'uid': self.uid,
            'name': self.nome_amigavel,
            'location': f'{self.coordenada_y}, {self.coordenada_x}' if self.coordenada_x and self.coordenada_y else None,
            'latitude': float(self.coordenada_y) if self.coordenada_y else None,
            'longitude': float(self.coordenada_x) if self.coordenada_x else None,
            'is_active': bool(self.ativa),
            'fill_level': self.nivel,
            'status': self.get_status(self.nivel),
            # 'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def get_status(self, fill_level):
        """
        Retorna o status baseado no nível de enchimento
        
        Args:
            fill_level (int): Percentual de enchimento
            
        Returns:
            str: Status do container
        """
        if fill_level >= 90:
            return 'Cheio'
        elif fill_level >= 70:
            return 'Alto'
        elif fill_level >= 40:
            return 'Médio'
        elif fill_level >= 20:
            return 'Baixo'
        else:
            return 'Vazio'
    
    def __repr__(self):
        return f'<{self.uid}: {self.nome_amigavel}>'

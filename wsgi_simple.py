from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*")

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/api/containers', methods=['GET'])
def get_containers():
    return jsonify({
        'success': True,
        'data': [],
        'total': 0
    }), 200

@app.route('/api/containers', methods=['POST'])
def create_container():
    return jsonify({
        'success': True,
        'message': 'Container criado com sucesso'
    }), 201

@app.route('/api/optimize-route', methods=['POST'])
def optimize_route():
    return jsonify({
        'success': False,
        'message': 'Nenhum container encontrado com nível >= 75%'
    }), 200

if __name__ == '__main__':
    app.run()

from flask import Flask
from models import init_db
from routes import bp

app = Flask(__name__)
app.register_blueprint(bp)

@app.route('/')
def root():
    return {'message': 'API para CriptoTrade P2P.'}

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
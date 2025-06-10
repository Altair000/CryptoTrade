from flask import Blueprint, request, jsonify
from models import get_db_connection
from auth import hash_password, verify_password, create_token, verify_token
from config import Config
from psycopg2 import sql

bp = Blueprint('routes', __name__)

@bp.route('/api/users/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    if not email or not username or not password:
        return jsonify({'error': 'Faltan datos'}), 400

    hashed = hash_password(password)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("INSERT INTO users (email, username, password, balance, telegram_id, name, age, identity_card) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"), (email, username, hashed, 0.0, data.get('telegram_id'), data.get('name'), data.get('age'), data.get('identity_card'))
                    )
        user_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({'message': 'Usuario registrado', 'user': {'id': user_id, 'email': email, 'username': username, 'balance': 0.0}}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Error al registrar', 'details': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@bp.route('/api/users/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("SELECT id, email, password, username, balance FROM users WHERE email=%s"), (email,))
        user = cur.fetchone()
        if not user or not verify_password(password, user[2]):
            return jsonify({'error': 'Usuario o Contraseña incorrecta.'}), 401
        token = create_token(user[0])
        return jsonify({'message': 'Login exitoso', 'token': token, 'user': {'id': user[0], 'email': user[1], 'username': user[3], 'balance': user[4]}})
    except Exception as e:
        return jsonify({'error': 'Error al iniciar sesion', 'details': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@bp.route('/api/users/check/<email>', methods=['GET'])
def check_user(email):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("SELECT id, email, username, balance FROM users WHERE telegram_id = %s"), (email,))
        user = cur.fetchone()
        if user:
            return jsonify({'exists': True, 'user': {'id': user[0], 'email': user[1], 'username': user[2], 'balance': user[3]}})
        return jsonify({'exists': False})
    except Exception as e:
        return jsonify({'error': 'Error al verificar', 'details': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@bp.route('/api/transactions/buy-balance', methods=['POST'])
def buy_balance():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Token inválido o expirado.'}), 401
    data = request.get_json()
    amount = data.get('amount')
    if not amount or amount <= 0:
        return jsonify({'error': 'Cantidad inválida.'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("INSERT INTO transactions (sender_id, receiver_wallet, amount, status) VALUES (%s, %s, %s, %s) RETURNING id"), (user_id, Config.ADMIN_WALLET, amount, 'pending')
                    )
        tx_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({'message': 'Solicitud de compra de saldo creada',
                        'transaction': {
                            'id': tx_id,
                            'sender_id': user_id,
                            'receiver_wallet': Config.ADMIN_WALLET,
                            'amount': amount,
                            'status': 'pendind'
                        }
                        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Error al crear transacción.', 'details': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@bp.route('/api/transactions/user/<int:user_id>', methods=['GET'])
def get_transactions(user_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not verify_token(token):
        return jsonify({'error': 'Token inválido o expirado.'}), 401
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("SELECT id, sender_id, receiver_wallet, amount, status, created_at, tx_hash FROM transactions WHERE sender_id = %s"), (user_id,)
                    )
        transactions = cur.fetchall()
        result = [
            {'id': transactions[0], 'sender_id': t[1], 'receiver_wallet': t[2], 'amount': t[3], 'status': t[4], 'created_at': t[5].isoformat(), 'tx_hash': t[6]}
            for t in transactions
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Error al obtener transacciones', 'details': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@bp.route('/api/offers', methods=['GET'])
def get_offers():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("SELECT id, user_id, type, amount, comment, status, created_at, FROM offers WHERE status = %s"),
                    ('active',)
                    )
        offers = cur.fetchall()
        result = [
            {'id': o[0], 'user_id': o[1], 'type': o[2], 'amount': o[3], 'comment': o[4], 'status': o[5], 'created_at': o[6].isoformat()}
            for o in offers
        ]
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Error al obtener ofertas', 'details': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@bp.route('/api/offers/create', methods=['POST'])
def create_offer():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401
    data = request.get_json()
    offer_type = data.get('type')
    amount = data.get('amount')
    comment = data.get('comment')
    if not all([offer_type, amount, comment]) or amount <= 0:
        return jsonify({'error': 'Datos inválidos'}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("INSERT INTO offers (user_id, type, amount, comment, status) VALUES (%s, %s, %s, %s, %s) RETURNING id"), (user_id, offer_type, amount, comment, 'active')
                    )
        offer_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({
            'message': 'Oferta Creada',
            'offer': {
                'id': offer_id,
                'user_id': user_id,
                'type': offer_type,
                'amount': amount,
                'comment': comment,
                'status': 'active'
            }
        }), 201
    except Exception as e:
        return jsonify({'error': 'Error al crear oferta', 'details': str(e)}), 400
    finally:
        cur.close()
        conn.close()

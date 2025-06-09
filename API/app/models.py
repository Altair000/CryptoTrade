import psycopg2
from psycopg2 import sql
from config import Config

def init_db():
    conn = psycopg2.connect(Config.DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            username VARCHAR(255) UNIQUE,
            password VARCHAR(255),
            wallet_address VARCHAR(255),
            balance FLOAT DEFAULT 0.0,
            telegram_id VARCHAR(50) UNIQUE,
            name VARCHAR(255),
            age INTEGER,
            identity_card VARCHAR(11),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            sender_id INTEGER REFERENCES users(id),
            receiver_wallet VARCHAR(255),
            amount FLOAT,
            status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tx_hash VARCHAR(255)
        );
        CREATE TABLE IF NOT EXISTS offers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            type VARCHAR(50),  -- 'buy' o 'sell'
            amount FLOAT,  -- Cantidad total de USDT
            min_amount FLOAT,  -- Límite mínimo
            max_amount FLOAT,  -- Límite máximo
            comment VARCHAR(500),  -- Comentario de la oferta
            status VARCHAR(50),  -- 'active', 'completed', 'canceled'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def get_db_connection():
    return psycopg2.connect(Config.DATABASE_URL)

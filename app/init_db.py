import os
import psycopg2
from psycopg2 import sql
from werkzeug.security import generate_password_hash

DB_NAME = "message_board"
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "yourpassword")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
conn = psycopg2.connect(
    dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
)
conn.autocommit = True
cur = conn.cursor()
cur.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [DB_NAME])
if not cur.fetchone():
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
    print(f"Database '{DB_NAME}' created.")
else:
    print(f"Database '{DB_NAME}' already exists.")
cur.close()
conn.close()
conn = psycopg2.connect(
    dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
)
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE
    );
    """
)
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
)
cur.execute("SELECT * FROM users WHERE username='admin'")
if not cur.fetchone():
    hashed_password = generate_password_hash("admin")
    cur.execute(
        "INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s)",
        ("admin", "admin", hashed_password, True),
    )
conn.commit()
cur.close()
conn.close()
print("Tables initialized in 'message_board' successfully.")

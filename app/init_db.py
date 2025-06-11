import os, psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL)
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
    from werkzeug.security import generate_password_hash

    hashed_password = generate_password_hash("admin")
    cur.execute(
        "INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s)",
        ("admin", "admin", hashed_password, True),
    )

conn.commit()
cur.close()
conn.close()
print("Database initialized successfully.")

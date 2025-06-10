from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

DB_PATH = 'messages.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()
        c.execute('INSERT INTO messages (name, message) VALUES (?, ?)', (data['name'], data['message']))
        conn.commit()
        return jsonify({'status': 'success'})

    else:
        c.execute('SELECT name, message FROM messages ORDER BY id DESC')
        messages = c.fetchall()
        return jsonify(messages)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)


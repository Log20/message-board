from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3, os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "secret")

DB_PATH = 'messages.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

@app.route('/')
def index():
    return render_template('index.html', is_admin=session.get('is_admin', False))

@app.route('/messages', methods=['GET', 'POST', 'DELETE'])
def messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()
        c.execute('INSERT INTO messages (name, message) VALUES (?, ?)', (data['name'], data['message']))
        conn.commit()
        return jsonify({'status': 'success'})

    elif request.method == 'DELETE':
        if not session.get('is_admin'):
            return jsonify({'error': 'Unauthorized'}), 401
        data = request.get_json()
        c.execute('DELETE FROM messages WHERE id = ?', (data['id'],))
        conn.commit()
        return jsonify({'status': 'deleted'})

    else:
        c.execute('SELECT id, name, message, created_at FROM messages ORDER BY id DESC')
        messages = c.fetchall()
        return jsonify(messages)

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return redirect('/login')
    return render_template('admin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_USERNAME and
            request.form['password'] == ADMIN_PASSWORD):
            session['is_admin'] = True
            return redirect('/admin')
        return render_template('login.html', error="登入失敗")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)

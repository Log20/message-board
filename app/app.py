from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")
DB_PATH = 'messages.db'

# -------------------- DB INIT --------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        # 自動新增 admin 帳戶，密碼為 admin（明文儲存）
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not user:
            conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', ('admin', 'admin', 1))

# -------------------- ROUTES --------------------
@app.route('/')
def index():
    return render_template('index.html', username=session.get('username'), is_admin=session.get('is_admin'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            return redirect('/login')
        except sqlite3.IntegrityError:
            return render_template('register.html', error='使用者已存在')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_PATH) as conn:
            user = conn.execute('SELECT id, password, is_admin FROM users WHERE username = ?', (username,)).fetchone()
            if user:
                if (username == 'admin' and password == 'admin') or check_password_hash(user[1], password):
                    session['user_id'] = user[0]
                    session['username'] = username
                    session['is_admin'] = bool(user[2])
                    return redirect('/')
        return render_template('login.html', error='登入失敗')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return redirect('/login')
    return render_template('admin.html', username=session.get('username'))

@app.route('/admin/change_password', methods=['POST'])
def change_password():
    if not session.get('is_admin'):
        return redirect('/login')
    username = request.form['username']
    new_password = generate_password_hash(request.form['new_password'])
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
    return redirect('/admin')

@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    if not session.get('is_admin'):
        return redirect('/login')
    username = request.form['username']
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('DELETE FROM users WHERE username = ?', (username,))
    return redirect('/admin')

@app.route('/messages', methods=['GET', 'POST', 'DELETE'])
def messages():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        if request.method == 'POST':
            if 'user_id' not in session:
                return jsonify({'error': '未登入'}), 401
            data = request.get_json()
            c.execute('INSERT INTO messages (user_id, message) VALUES (?, ?)', (session['user_id'], data['message']))
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
            c.execute('''
                SELECT m.id, u.username, m.message, m.created_at
                FROM messages m
                LEFT JOIN users u ON m.user_id = u.id
                ORDER BY m.id DESC
            ''')
            return jsonify(c.fetchall())

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
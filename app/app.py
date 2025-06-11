import os, psycopg2, secrets
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify,
    url_for,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import subprocess

subprocess.call(["python", "app/init_db.py"])

app = Flask(__name__)
oauth = OAuth(app)
app.secret_key = os.getenv("SECRET_KEY", "dev")
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    },
)
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


@app.route("/")
def index():
    return render_template(
        "index.html", username=session.get("username"), is_admin=session.get("is_admin")
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template("register.html", error="此 Email 已被使用")
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password),
            )
            conn.commit()
            cur.close()
            conn.close()
            return redirect("/login?success=registered")
        except Exception as e:
            if conn:
                conn.rollback()
            return render_template("register.html", error="註冊失敗，請稍後再試")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password, is_admin FROM users WHERE email = %s",
            (email,),
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["email"] = user[2]
            session["is_admin"] = user[3]
            return redirect("/?success=login")
        return render_template("login.html", error="登入失敗")
    return render_template("login.html")


@app.route("/login/google")
def login_google():
    nonce = secrets.token_urlsafe(16)
    session["nonce"] = nonce
    redirect_uri = url_for("authorize_google", _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)


@app.route("/authorize/google")
def authorize_google():
    token = google.authorize_access_token()
    nonce = session.pop("nonce", None)
    user_info = google.parse_id_token(token, nonce=nonce)
    email = user_info.get("email")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    if not user:
        cur.execute(
            "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
            (email, generate_password_hash(os.urandom(8).hex()), email),
        )
        conn.commit()
        cur.execute("SELECT id, username FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
    session["user_id"] = user[0]
    session["username"] = user[1]
    session["is_admin"] = False
    cur.close()
    conn.close()
    return redirect("/?success=registered_google")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/?success=logout")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = request.form.get("email")
        new_password = request.form.get("new_password")
        conn = get_db_connection()
        cur = conn.cursor()
        if email and not new_password:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            if user:
                return render_template("reset_password.html", email=email, step=2)
            else:
                return render_template(
                    "reset_password.html", error="找不到此 Email", step=1
                )
        elif email and new_password:
            hashed_pw = generate_password_hash(new_password)
            cur.execute(
                "UPDATE users SET password = %s WHERE email = %s", (hashed_pw, email)
            )
            conn.commit()
            cur.close()
            conn.close()
            return redirect("/login?success=password_changed")
    return render_template("reset_password.html", step=1)


@app.route("/profile", methods=["GET", "POST"])
def user_profile():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, email, password FROM users WHERE id = %s",
        (session["user_id"],),
    )
    user = cur.fetchone()
    if not user:
        cur.close()
        conn.close()
        session.clear()
        return redirect("/login")
    username, email, hashed_password = user
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        if not check_password_hash(hashed_password, old_password):
            cur.close()
            conn.close()
            return render_template(
                "profile.html", username=username, email=email, error="舊密碼錯誤"
            )
        new_hashed = generate_password_hash(new_password)
        cur.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (new_hashed, session["user_id"]),
        )
        conn.commit()
        cur.close()
        conn.close()
        session.clear()
        return redirect("/login?success=password_changed")
    cur.close()
    conn.close()
    return render_template("profile.html", username=username, email=email)


@app.route("/admin")
def admin_panel():
    if not session.get("is_admin"):
        return redirect("/")
    return render_template("admin.html", username=session.get("username"))


@app.route("/messages", methods=["GET", "POST", "DELETE"])
def messages():
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == "POST":
        if "user_id" not in session:
            return jsonify({"error": "未登入"}), 401
        data = request.get_json()
        cur.execute(
            "INSERT INTO messages (user_id, message) VALUES (%s, %s)",
            (session["user_id"], data["message"]),
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "success"})
    elif request.method == "DELETE":
        if not session.get("is_admin"):
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json()
        cur.execute("DELETE FROM messages WHERE id = %s", (data["id"],))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "deleted"})
    else:
        cur.execute(
            """
            SELECT m.id, u.username, m.message, m.created_at
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            ORDER BY m.id DESC
        """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)


@app.route("/delete_account", methods=["POST"])
def delete_account():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    password = request.form.get("password")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if not user or not check_password_hash(user[0], password):
        cur.close()
        conn.close()
        flash("密碼錯誤，無法刪除帳號", "error")
        return redirect("/profile")
    cur.execute(
        """
        UPDATE users
        SET username = '已刪除',
            email = '已刪除',
            password = '已刪除',
            is_admin = FALSE 
        WHERE id = %s
        """,
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()
    session.clear()
    flash("帳號已成功刪除", "success")
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename

import sqlite3
import uuid
import os
import requests

app = Flask(__name__)
app.secret_key = "1234"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "img", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

connection = sqlite3.connect("sqlite.db", check_same_thread=False)
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    bio TEXT,
    github TEXT,
    telegram TEXT,
    avatar TEXT,
    skills TEXT
)
''')

connection.commit()
connection.close()

@app.route("/")
def hello_world():
    theme = session.get('theme', 'light')

    conn = sqlite3.connect("sqlite.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    conn.close()

    filter_skill = request.args.get('skill')
    if filter_skill:
        filter_skill = filter_skill.strip().lower()
    else:
        filter_skill = None

    portfolios = []
    for row in rows:
        # skills z DB jako string
        skills_str = row["skills"] or ""
        # filtr podle skills
        skills_lower = [s.strip().lower() for s in skills_str.split(",") if s.strip()]
        if filter_skill is None or filter_skill in skills_lower:
            portfolios.append(row)

    tool_icons = {
        "Python": "🐍", "Flask": "🌶️", "HTML": "🗒️", "CSS": "🎨", "HTML/CSS": "🖌️",
        "Git": "🔧", "GitHub": "🧘", "Telegram": "✈️", "SQL": "🗄️", "SQLite": "📘",
        "JavaScript": "⚡️", "JS": "⚡️", "Jinja": "🧩"
    }

    return render_template(
        "all_portfolios.html",
        portfolios=portfolios,
        theme=theme,
        tool_icons=tool_icons,
        current_skill=filter_skill or ""
    )

@app.route("/generate", methods=["POST"])
def generate_portfolio():
    form = request.form
    avatar_file = request.files.get("avatar")

    name = form.get("name")
    bio = form.get("bio")
    github = form.get("github")
    telegram = form.get("telegram")
    skills = form.get("skills")

    user_uuid = str(uuid.uuid4())

    if avatar_file and avatar_file.filename != "":
        filename = secure_filename(avatar_file.filename)

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        avatar_file.save(save_path)

        avatar_path = f"img/uploads/{filename}"

    else:
        avatar_path = "img/avatars/placeholder.png"

    conn = sqlite3.connect("sqlite.db")
    cursor = conn.cursor()

    cursor.execute("""
            INSERT INTO users (uuid, name, bio, github, telegram, avatar, skills)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_uuid, name, bio, github, telegram, avatar_path, skills))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route('/form', methods=["GET"])
def form():

    return render_template('form.html')

@app.route('/portfolio/<uuid>')
def view_portfolio(uuid):
    conn = sqlite3.connect("sqlite.db")
    conn.row_factory = sqlite3.Row  # so we can access columns by name in template
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
    user = cursor.fetchone()

    conn.close()

    tool_icons = {
        "Python": "🐍", "Flask": "🌶️", "HTML": "🗒️", "CSS": "🎨", "HTML/CSS": "🖌️", "Git": "🔧", "GitHub": "🧘", "Telegram": "✈️", "SQL": "🗄️", "SQLite": "📘", "JavaScript": "⚡️", "JS": "⚡️", "Jinja": "🧩"
    }

    if user is None:
        return "Portfolio not found", 404

    raw_skills = user["skills"] or ""
    skills = [s.strip() for s in raw_skills.split(",") if s.strip()]

    projects = []  # empty list for projects

    github_value = user["github"]

    if github_value:
        # User in DB may have either username OR full URL
        github_username = github_value.strip()

        # If it's a full URL like "https://github.com/anderajan-sys"
        if "github.com" in github_username:
            github_username = github_username.rstrip("/").split("/")[-1]

        api_url = f"https://api.github.com/users/{github_username}/repos"

        try:
            response = requests.get(api_url, timeout=5)

            if response.ok:
                repos = response.json()  # list of repo dicts
                print(repos)
                for repo in repos[:6]:  # first 6 only
                    projects.append(
                        {
                            "title": repo.get("name"),
                            "description": repo.get("description") or "No description",
                            "link": repo.get("html_url"),
                        }
                    )
            else:
                # e.g., 404, rate limit, etc.
                app.logger.warning(
                    f"GitHub request failed for user {github_username}: "
                    f"status {response.status_code}"
                )

        except requests.RequestException as e:
            # Network / timeout / DNS etc.
            app.logger.error(f"Error while requesting GitHub API: {e}")

    return render_template("portfolio_template.html", user=user, skills=skills, projects=projects, tool_icons=tool_icons)

@app.route('/set_theme/<theme>')
def set_theme(theme):
    if theme in ['light', 'dark']:
        session['theme'] = theme

    next_url = request.args.get('next') or url_for('hello_world')
    return redirect(next_url)

if __name__ == "__main__":
    app.run()



from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, ast, subprocess, tempfile, time, sys
from pathlib import Path
from functools import wraps

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "codemind.db"
app = Flask(__name__)
app.secret_key = os.environ.get("CODEMIND_SECRET", "change-this-dev-secret")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, action TEXT NOT NULL,
            details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("INSERT OR IGNORE INTO users(username,password) VALUES(?,?)", ("demo", "codemind123"))

def log_action(action, details=""):
    if session.get("username"):
        with db() as conn:
            conn.execute("INSERT INTO history(username,action,details) VALUES(?,?,?)",
                         (session["username"], action, details[:500]))

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("dashboard") if session.get("username") else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            session["username"] = username
            log_action("Login", "Successful sign in")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password. Try demo / codemind123.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as conn:
        recent = conn.execute("SELECT * FROM history WHERE username=? ORDER BY id DESC LIMIT 6",
                              (session["username"],)).fetchall()
        total = conn.execute("SELECT COUNT(*) n FROM history WHERE username=?", (session["username"],)).fetchone()["n"]
    return render_template("dashboard.html", recent=recent, total=total)

@app.route("/workspace", methods=["GET", "POST"])
@login_required
def workspace():
    code = request.form.get("code", 'def greet(name):\n    return f"Hello, {name}!"\n\nprint(greet("CodeMind"))')
    output, error, elapsed = "", "", None
    if request.method == "POST":
        action = request.form.get("action", "run")
        if action == "run":
            # Demo runner: do not expose this to untrusted public users without a real sandbox.
            try:
                with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
                    f.write(code)
                    temp_name = f.name
                start = time.perf_counter()
                result = subprocess.run([sys.executable, "-I", temp_name], capture_output=True, text=True, timeout=3,
                                        cwd=str(APP_DIR), env={"PATH": os.environ.get("PATH", "")})
                elapsed = round(time.perf_counter() - start, 4)
                output = result.stdout[:6000]
                error = result.stderr[:6000]
                if result.returncode and not error:
                    error = f"Program exited with code {result.returncode}"
            except subprocess.TimeoutExpired:
                error = "Execution timed out after 3 seconds."
            except Exception as exc:
                error = str(exc)
            finally:
                try: os.unlink(temp_name)
                except Exception: pass
            log_action("Code execution", f"Runtime: {elapsed}s")
        elif action == "analyze":
            return redirect(url_for("analyzer", code=code))
    return render_template("workspace.html", code=code, output=output, error=error, elapsed=elapsed)

def analyze_python(code):
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [{"severity":"Error", "line":exc.lineno or 1, "message":f"Syntax error: {exc.msg}"}], None
    lines = code.splitlines()
    if len(lines) > 200:
        issues.append({"severity":"Info", "line":1, "message":f"Large file: {len(lines)} lines. Consider splitting it into modules."})
    for no, line in enumerate(lines, 1):
        stripped = line.strip()
        if len(line) > 100:
            issues.append({"severity":"Warning", "line":no, "message":"Line exceeds 100 characters."})
        if stripped.startswith("print("):
            issues.append({"severity":"Info", "line":no, "message":"Print statement found; use logging for production applications."})
        if "==" in stripped and ("if " in stripped) and stripped.endswith("== True:"):
            issues.append({"severity":"Suggestion", "line":no, "message":"Use the boolean expression directly instead of '== True'."})
        if stripped == "except:":
            issues.append({"severity":"Warning", "line":no, "message":"Bare except catches every exception; catch a specific exception."})
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    assigned_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    loaded_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for name in sorted(assigned_names - loaded_names):
        if not name.startswith("_"):
            issues.append({"severity":"Suggestion", "line":1, "message":f"'{name}' may be assigned but never read (basic heuristic)."})
    metrics = {"lines":len(lines), "functions":len(functions), "classes":len(classes), "imports":len(imports)}
    if not issues:
        issues.append({"severity":"Success", "line":1, "message":"No issues found by the built-in checks."})
    return issues, metrics

@app.route("/analyzer", methods=["GET", "POST"])
@login_required
def analyzer():
    code = request.form.get("code", request.args.get("code", 'def add(a, b):\n    return a + b\n'))
    issues, metrics = analyze_python(code)
    if request.method == "POST":
        log_action("Code analysis", f"{len(issues)} findings")
    return render_template("analyzer.html", code=code, issues=issues, metrics=metrics)

@app.route("/tests", methods=["GET", "POST"])
@login_required
def tests():
    code = request.form.get("code", 'def add(a, b):\n    return a + b\n')
    result = None
    if request.method == "POST":
        function_name = request.form.get("function_name", "add").strip()
        raw_cases = request.form.get("cases", "1,2,3\n2,5,7\n-1,1,0")
        try:
            namespace = {}
            # Demo only: user code is executed; do not deploy publicly without sandbox isolation.
            exec(compile(code, "<user_code>", "exec"), {"__builtins__": {"range": range, "len": len, "sum": sum, "min": min, "max": max, "abs": abs}}, namespace)
            fn = namespace.get(function_name)
            if not callable(fn):
                raise ValueError(f"Function '{function_name}' was not found.")
            rows = []
            for line in raw_cases.splitlines()[:30]:
                if not line.strip(): continue
                args = [eval(part.strip(), {"__builtins__": {}}, {}) for part in line.split(",")]
                try:
                    value = fn(*args)
                    rows.append({"input":line, "output":repr(value), "status":"Passed"})
                except Exception as exc:
                    rows.append({"input":line, "output":str(exc), "status":"Failed"})
            result = rows
            log_action("Test generation", f"{len(rows)} test cases")
        except Exception as exc:
            result = [{"input":"—", "output":str(exc), "status":"Error"}]
    return render_template("tests.html", code=code, result=result)

@app.route("/projects")
@login_required
def projects():
    with db() as conn:
        rows = conn.execute("SELECT * FROM history WHERE username=? ORDER BY id DESC LIMIT 50",
                            (session["username"],)).fetchall()
    return render_template("projects.html", history=rows)

@app.route("/api/health")
def health():
    return jsonify({"status":"ok", "app":"CodeMind AI", "api_key_required":False})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

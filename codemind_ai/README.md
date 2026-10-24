# CodeMind AI — Intelligent Engineering Workspace

A no-paid-API-key Flask prototype for a final-year project. Includes a login screen with a bundled illustration, dashboard, Python workspace, basic static analyzer, function test runner, and activity history.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create a virtual environment (recommended):
   - Windows: `py -m venv .venv`
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start: `python app.py`
6. Open `http://127.0.0.1:5000`

## Demo login

- Username: `demo`
- Password: `codemind123`

The database is created automatically on first run.

## Modules

1. Login and dashboard
2. Python code editor and local execution
3. Rule-based syntax and code-quality analysis
4. Basic function test runner
5. Project/activity history
6. Metrics and results display

## Important security note

This is a local educational prototype, not production-hardened software. The code runner and test runner execute submitted Python code. Keep the app on your own computer and do not expose it to the public internet. For real multi-user deployment, run code in a hardened isolated container/VM with strict CPU, memory, filesystem, and network restrictions. The demo login stores a simple sample password and must be replaced with password hashing and proper user management before deployment.

No external AI API key is required because the included “smart” checks use local Python logic rather than a hosted LLM.

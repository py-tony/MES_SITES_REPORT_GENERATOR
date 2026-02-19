MES Report Generator

Quick setup (Windows):

1. Create & activate a venv
```
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies

```
pip install -r requirements.txt
```

3. Copy the binary logo into the deploy static folder

- Copy `siteReportsApp\static\logo.png` into `mes_report_generator\static\logo.png`.

4. Run the app

```
set FLASK_APP=app.py
flask run
```

Default account (created on first run):
- username: IT
- password: Mes@2026

Notes:
- If you plan to deploy on PythonAnywhere, use `wsgi.py` provided and upload the entire `mes_report_generator` folder.
- Verify `instance/` path permissions for SQLite file creation.
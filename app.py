from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import sqlite3
from datetime import datetime
import os
from io import BytesIO
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

app = Flask(__name__)
app.secret_key = "mes_report_app_secret_key_2026"

DB_PATH = os.path.join(app.instance_path, "site_reports.db")


# ----------------------------
# DB helpers
# ----------------------------
def get_db():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_name TEXT NOT NULL,
        location TEXT,
        report_type TEXT NOT NULL,
        period_start TEXT,
        period_end TEXT,
        prepared_by TEXT,
        department TEXT,
        date_submitted TEXT,
        prepared_by_title TEXT,
        office_manager TEXT,
        director_it TEXT,

        executive_summary TEXT,
        overall_status TEXT,

        network_status TEXT,
        power_status TEXT,
        hardware_status TEXT,
        biomedical_status TEXT,
        cameras_live INTEGER DEFAULT 0,
        cameras_down INTEGER DEFAULT 0,
        biometrics_live INTEGER DEFAULT 0,
        biometrics_down INTEGER DEFAULT 0,
        software_status TEXT,
        security_status TEXT,

        recommendations TEXT,
        risks_constraints TEXT,
        conclusion TEXT,

        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        issue_title TEXT NOT NULL,
        area TEXT,
        impact TEXT,
        status TEXT,
        owner TEXT,
        action_taken TEXT,
        root_cause TEXT,
        pending_reason TEXT,
        priority TEXT,
        target_date TEXT,
        responsible TEXT,
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        device_name TEXT NOT NULL,
        hostname TEXT,
        serial_number TEXT,
        status TEXT,
        FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    
    # Initialize default account if it doesn't exist
    try:
        existing_user = cur.execute("SELECT id FROM users WHERE username = ?", ("IT",)).fetchone()
        if not existing_user:
            default_password = generate_password_hash("Mes@2026")
            cur.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                ("IT", default_password, datetime.utcnow().isoformat())
            )
            conn.commit()
    except Exception:
        pass

    # Ensure new columns exist for existing DBs (backwards-compatible migration)
    existing_cols = [r[1] for r in cur.execute("PRAGMA table_info(reports)").fetchall()]
    alter_stmts = []
    if 'cameras_live' not in existing_cols:
        alter_stmts.append("ALTER TABLE reports ADD COLUMN cameras_live INTEGER DEFAULT 0")
    if 'cameras_down' not in existing_cols:
        alter_stmts.append("ALTER TABLE reports ADD COLUMN cameras_down INTEGER DEFAULT 0")
    if 'biometrics_live' not in existing_cols:
        alter_stmts.append("ALTER TABLE reports ADD COLUMN biometrics_live INTEGER DEFAULT 0")
    if 'biometrics_down' not in existing_cols:
        alter_stmts.append("ALTER TABLE reports ADD COLUMN biometrics_down INTEGER DEFAULT 0")
    if 'office_manager' not in existing_cols:
        alter_stmts.append("ALTER TABLE reports ADD COLUMN office_manager TEXT")
    if 'director_it' not in existing_cols:
        alter_stmts.append("ALTER TABLE reports ADD COLUMN director_it TEXT")
    if 'prepared_by_title' not in existing_cols:
        alter_stmts.append("ALTER TABLE reports ADD COLUMN prepared_by_title TEXT")

    for s in alter_stmts:
        try:
            cur.execute(s)
        except Exception:
            pass

    conn.commit()
    conn.close()


@app.before_request
def startup():
    init_db()


# ----------------------------
# Authentication helpers
# ----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        cur = conn.cursor()
        user = cur.execute("SELECT id, username, password FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session['user_id'] = user["id"]
            session['username'] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required.", "warning")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "warning")
            return redirect(url_for("register"))

        conn = get_db()
        cur = conn.cursor()

        try:
            hashed_password = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, hashed_password, datetime.utcnow().isoformat())
            )
            conn.commit()
            flash(f"Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ----------------------------
# Protected Routes
# ----------------------------
@app.route("/")
@login_required
def index():
    site = request.args.get("site", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()

    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT r.*,
        (SELECT COUNT(*) FROM issues i WHERE i.report_id = r.id AND i.status != 'Resolved') AS open_issues
        FROM reports r
        WHERE 1=1
    """
    params = []

    if site:
        query += " AND r.site_name LIKE ?"
        params.append(f"%{site}%")

    if status:
        query += " AND r.overall_status = ?"
        params.append(status)

    query += " ORDER BY r.created_at DESC"

    reports = cur.execute(query, params).fetchall()

    # priority filter needs joining issues
    if priority:
        reports_filtered = []
        for r in reports:
            p = cur.execute(
                "SELECT COUNT(*) AS c FROM issues WHERE report_id = ? AND priority = ?",
                (r["id"], priority)
            ).fetchone()["c"]
            if p > 0:
                reports_filtered.append(r)
        reports = reports_filtered

    conn.close()

    # Aggregate stats for the displayed reports
    total_reports = len(reports)
    total_open_issues = sum([r["open_issues"] or 0 for r in reports])

    # Counts by overall_status for displayed reports
    status_counts = {"Good": 0, "Stable": 0, "Needs Attention": 0, "Critical": 0}
    for r in reports:
        s = r["overall_status"] or ""
        if s in status_counts:
            status_counts[s] += 1

    # Devices summary across displayed reports
    device_total = 0
    device_broken = 0
    report_ids = [r["id"] for r in reports]
    if report_ids:
        conn = get_db()
        cur = conn.cursor()
        q = f"SELECT COUNT(*) AS c FROM devices WHERE report_id IN ({','.join('?'*len(report_ids))})"
        device_total = cur.execute(q, report_ids).fetchone()["c"]
        q2 = f"SELECT COUNT(*) AS c FROM devices WHERE report_id IN ({','.join('?'*len(report_ids))}) AND status = ?"
        device_broken = cur.execute(q2, report_ids + ["Broken"]).fetchone()["c"]
        conn.close()

    return render_template(
        "index.html",
        reports=reports,
        site=site,
        status=status,
        priority=priority,
        total_reports=total_reports,
        total_open_issues=total_open_issues,
        status_counts=status_counts,
        device_total=device_total,
        device_broken=device_broken,
    )


@app.route("/report/new", methods=["GET", "POST"])
@login_required
def new_report():
    if request.method == "POST":
        data = request.form

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO reports (
                site_name, location, report_type, period_start, period_end,
                prepared_by, department, date_submitted, prepared_by_title, office_manager, director_it,
                executive_summary, overall_status,
                network_status, power_status, hardware_status, biomedical_status,
                cameras_live, cameras_down, biometrics_live, biometrics_down,
                software_status, security_status,
                recommendations, risks_constraints, conclusion,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("site_name"),
            data.get("location"),
            data.get("report_type"),
            data.get("period_start"),
            data.get("period_end"),
            data.get("prepared_by"),
            data.get("department"),
            data.get("date_submitted"),
            data.get("prepared_by_title"),
            data.get("office_manager"),
            data.get("director_it"),
            data.get("executive_summary"),
            data.get("overall_status"),
            data.get("network_status"),
            data.get("power_status"),
            data.get("hardware_status"),
            data.get("biomedical_status"),
            data.get("cameras_live"),
            data.get("cameras_down"),
            data.get("biometrics_live"),
            data.get("biometrics_down"),
            data.get("software_status"),
            data.get("security_status"),
            data.get("recommendations"),
            data.get("risks_constraints"),
            data.get("conclusion"),
            datetime.utcnow().isoformat()
        ))

        report_id = cur.lastrowid

        # Issues (dynamic)
        issue_titles = request.form.getlist("issue_title[]")
        areas = request.form.getlist("area[]")
        impacts = request.form.getlist("impact[]")
        statuses = request.form.getlist("issue_status[]")
        owners = request.form.getlist("owner[]")
        actions = request.form.getlist("action_taken[]")
        root_causes = request.form.getlist("root_cause[]")
        priorities = request.form.getlist("priority[]")
        target_dates = request.form.getlist("target_date[]")
        responsibles = request.form.getlist("responsible[]")

        for idx in range(len(issue_titles)):
            title = issue_titles[idx].strip() if idx < len(issue_titles) else ""
            if not title:
                continue

            cur.execute("""
                INSERT INTO issues (
                    report_id, issue_title, area, impact, status, owner,
                    action_taken, root_cause, priority, target_date, responsible
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                title,
                areas[idx] if idx < len(areas) else "",
                impacts[idx] if idx < len(impacts) else "",
                statuses[idx] if idx < len(statuses) else "",
                owners[idx] if idx < len(owners) else "",
                actions[idx] if idx < len(actions) else "",
                root_causes[idx] if idx < len(root_causes) else "",
                priorities[idx] if idx < len(priorities) else "",
                target_dates[idx] if idx < len(target_dates) else "",
                responsibles[idx] if idx < len(responsibles) else ""
            ))

        # Devices (dynamic)
        device_names = request.form.getlist("device_name[]")
        hostnames = request.form.getlist("hostname[]")
        serials = request.form.getlist("serial_number[]")
        dev_statuses = request.form.getlist("device_status[]")

        for idx in range(len(device_names)):
            dname = device_names[idx].strip() if idx < len(device_names) else ""
            if not dname:
                continue

            cur.execute("""
                INSERT INTO devices (
                    report_id, device_name, hostname, serial_number, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                report_id,
                dname,
                hostnames[idx] if idx < len(hostnames) else "",
                serials[idx] if idx < len(serials) else "",
                dev_statuses[idx] if idx < len(dev_statuses) else ""
            ))

        conn.commit()
        conn.close()

        flash("Report saved successfully!", "success")
        return redirect(url_for("report_detail", report_id=report_id))

    return render_template("new_report.html")


@app.route("/report/<int:report_id>")
@login_required
def report_detail(report_id):
    conn = get_db()
    cur = conn.cursor()

    report = cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    issues = cur.execute("SELECT * FROM issues WHERE report_id = ? ORDER BY id DESC", (report_id,)).fetchall()
    devices = cur.execute("SELECT * FROM devices WHERE report_id = ? ORDER BY id DESC", (report_id,)).fetchall()
    devices = cur.execute("SELECT * FROM devices WHERE report_id = ? ORDER BY id DESC", (report_id,)).fetchall()

    conn.close()

    if not report:
        flash("Report not found.", "danger")
        return redirect(url_for("index"))

    return render_template("report_detail.html", report=report, issues=issues, devices=devices)


@app.route("/report/<int:report_id>/edit", methods=["GET", "POST"])
@login_required
def edit_report(report_id):
    conn = get_db()
    cur = conn.cursor()

    report = cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    issues = cur.execute("SELECT * FROM issues WHERE report_id = ? ORDER BY id DESC", (report_id,)).fetchall()

    if not report:
        conn.close()
        flash("Report not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        data = request.form

        cur.execute("""
            UPDATE reports SET
                site_name=?, location=?, report_type=?, period_start=?, period_end=?,
                prepared_by=?, department=?, date_submitted=?, prepared_by_title=?, office_manager=?, director_it=?,
                executive_summary=?, overall_status=?,
                network_status=?, power_status=?, hardware_status=?, biomedical_status=?,
                cameras_live=?, cameras_down=?, biometrics_live=?, biometrics_down=?,
                software_status=?, security_status=?,
                recommendations=?, risks_constraints=?, conclusion=?
            WHERE id=?
        """, (
            data.get("site_name"),
            data.get("location"),
            data.get("report_type"),
            data.get("period_start"),
            data.get("period_end"),
            data.get("prepared_by"),
            data.get("department"),
            data.get("date_submitted"),
            data.get("prepared_by_title"),
            data.get("office_manager"),
            data.get("director_it"),
            data.get("executive_summary"),
            data.get("overall_status"),
            data.get("network_status"),
            data.get("power_status"),
            data.get("hardware_status"),
            data.get("biomedical_status"),
            data.get("cameras_live"),
            data.get("cameras_down"),
            data.get("biometrics_live"),
            data.get("biometrics_down"),
            data.get("software_status"),
            data.get("security_status"),
            data.get("recommendations"),
            data.get("risks_constraints"),
            data.get("conclusion"),
            report_id
        ))

        # Clear old issues then re-add
        cur.execute("DELETE FROM issues WHERE report_id = ?", (report_id,))
        # Clear old devices then re-add
        cur.execute("DELETE FROM devices WHERE report_id = ?", (report_id,))

        issue_titles = request.form.getlist("issue_title[]")
        areas = request.form.getlist("area[]")
        impacts = request.form.getlist("impact[]")
        statuses = request.form.getlist("issue_status[]")
        owners = request.form.getlist("owner[]")
        actions = request.form.getlist("action_taken[]")
        root_causes = request.form.getlist("root_cause[]")
        priorities = request.form.getlist("priority[]")
        target_dates = request.form.getlist("target_date[]")
        responsibles = request.form.getlist("responsible[]")

        for idx in range(len(issue_titles)):
            title = issue_titles[idx].strip() if idx < len(issue_titles) else ""
            if not title:
                continue

            cur.execute("""
                INSERT INTO issues (
                    report_id, issue_title, area, impact, status, owner,
                    action_taken, root_cause, priority, target_date, responsible
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                title,
                areas[idx] if idx < len(areas) else "",
                impacts[idx] if idx < len(impacts) else "",
                statuses[idx] if idx < len(statuses) else "",
                owners[idx] if idx < len(owners) else "",
                actions[idx] if idx < len(actions) else "",
                root_causes[idx] if idx < len(root_causes) else "",
                priorities[idx] if idx < len(priorities) else "",
                target_dates[idx] if idx < len(target_dates) else "",
                responsibles[idx] if idx < len(responsibles) else ""
            ))

        # Re-add devices
        device_names = request.form.getlist("device_name[]")
        hostnames = request.form.getlist("hostname[]")
        serials = request.form.getlist("serial_number[]")
        dev_statuses = request.form.getlist("device_status[]")

        for idx in range(len(device_names)):
            dname = device_names[idx].strip() if idx < len(device_names) else ""
            if not dname:
                continue

            cur.execute("""
                INSERT INTO devices (
                    report_id, device_name, hostname, serial_number, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                report_id,
                dname,
                hostnames[idx] if idx < len(hostnames) else "",
                serials[idx] if idx < len(serials) else "",
                dev_statuses[idx] if idx < len(dev_statuses) else ""
            ))

        conn.commit()
        conn.close()

        flash("Report updated successfully!", "success")
        return redirect(url_for("report_detail", report_id=report_id))

    conn.close()
    return render_template("edit_report.html", report=report, issues=issues)


@app.route("/report/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_report(report_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()

    flash("Report deleted.", "info")
    return redirect(url_for("index"))


@app.route("/report/<int:report_id>/download")
@login_required
def download_report(report_id):
    conn = get_db()
    cur = conn.cursor()

    report = cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    issues = cur.execute("SELECT * FROM issues WHERE report_id = ? ORDER BY id DESC", (report_id,)).fetchall()

    conn.close()

    if not report:
        flash("Report not found.", "danger")
        return redirect(url_for("index"))

    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#1a2c47"),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=6,
        spaceBefore=12
    )

    # Title
    story.append(Paragraph("SITE REPORT DETAIL", title_style))
    story.append(Spacer(1, 0.2*inch))

    # Report header info
    header_data = [
        ["Site Name:", report["site_name"]],
        ["Location:", report["location"] or "-"],
        ["Report Type:", report["report_type"]],
        ["Period Start:", report["period_start"] or "-"],
        ["Period End:", report["period_end"] or "-"],
        ["Prepared By:", report["prepared_by"] or "-"],
        ["Prepared By Title:", report["prepared_by_title"] or "-"],
        ["Department:", report["department"] or "-"],
        ["Office Manager:", report["office_manager"] or "-"],
        ["Director of IT Department:", report["director_it"] or "-"],
        ["Date Submitted:", report["date_submitted"] or "-"],
        ["Overall Status:", report["overall_status"] or "-"]
    ]
    header_table = Table(header_data, colWidths=[1.5*inch, 4*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f0f8')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*inch))

    # Executive Summary
    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    story.append(Paragraph(report["executive_summary"] or "-", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Status Overview
    story.append(Paragraph("STATUS OVERVIEW", heading_style))
    status_data = [
        ["Category", "Status"],
        ["Network", report["network_status"] or "-"],
        ["Power", report["power_status"] or "-"],
        ["Hardware", report["hardware_status"] or "-"],
        ["Cameras", f"{report['cameras_live'] or '-'} live / {report['cameras_down'] or '-'} down"],
        ["Biometrics", f"{report['biometrics_live'] or '-'} live / {report['biometrics_down'] or '-'} down"],
        ["Software", report["software_status"] or "-"],
        ["Security", report["security_status"] or "-"]
    ]
    status_table = Table(status_data, colWidths=[2.5*inch, 3*inch])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    story.append(status_table)
    story.append(Spacer(1, 0.2*inch))

    # Issues
    if issues:
        story.append(Paragraph("ISSUES LOGGED", heading_style))
        issues_data = [["Issue Title", "Area", "Impact", "Status", "Priority", "Owner"]]
        for issue in issues:
            issues_data.append([
                issue["issue_title"] or "-",
                issue["area"] or "-",
                issue["impact"] or "-",
                issue["status"] or "-",
                issue["priority"] or "-",
                issue["owner"] or "-"
            ])
        issues_table = Table(issues_data, colWidths=[1.2*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.8*inch])
        issues_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4)
        ]))
        story.append(issues_table)
        story.append(Spacer(1, 0.2*inch))

    # Recommendations
    story.append(Paragraph("RECOMMENDATIONS", heading_style))
    story.append(Paragraph(report["recommendations"] or "-", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Risks & Constraints
    story.append(Paragraph("RISKS & CONSTRAINTS", heading_style))
    story.append(Paragraph(report["risks_constraints"] or "-", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Conclusion
    story.append(Paragraph("CONCLUSION", heading_style))
    story.append(Paragraph(report["conclusion"] or "-", styles['Normal']))

    # Build PDF
    # Draw logo on the first page
    def on_first_page(canvas, doc_obj):
        canvas.saveState()
        width, height = doc_obj.pagesize
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
        
        if os.path.exists(logo_path):
            try:
                logo_width = 1.8 * inch
                logo_height = 0.45 * inch
                logo_x = doc_obj.leftMargin
                logo_y = height - logo_height - 0.35 * inch
                canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True)
            except Exception:
                pass
        canvas.restoreState()

    doc.build(story, onFirstPage=on_first_page)
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{report['site_name']}_Report_{report_id}.pdf"
    )


if __name__ == "__main__":
    app.run(debug=True)

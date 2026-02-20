# MES Report Generator - Authentication System Documentation

## Quick Start

### Setup Instructions (Windows)

1. **Create & activate a virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Copy logo file**
- Copy `logo.png` from design assets into `mes_report_generator\static\logo.png`

4. **Run the application**
```bash
set FLASK_APP=app.py
flask run
```

The application will start at `http://localhost:5000`

---

## Table of Contents

1. [Authentication System Overview](#authentication-system-overview)
2. [User Roles and Permissions](#user-roles-and-permissions)
3. [Default Accounts](#default-accounts)
4. [Registration Process](#registration-process)
5. [Email Verification](#email-verification)
6. [Access Control](#access-control)
7. [Security Features](#security-features)
8. [Configuration](#configuration)
9. [Protected Routes](#protected-routes)
10. [Troubleshooting](#troubleshooting)

---

## Authentication System Overview

### Technology Stack

- **Framework:** Flask 3.0.0
- **Login Management:** Flask-Login 0.6.2
- **Password Security:** Werkzeug 3.0.0 (PBKDF2 hashing)
- **Database:** SQLite 3
- **Email Notifications:** SMTP (optional, with python-dotenv)

### Key Features

✓ Secure password hashing using PBKDF2  
✓ Flask-Login session management  
✓ Role-based access control (Admin / Technician)  
✓ Email verification workflow for new registrations  
✓ Admin email notifications for new user signups  
✓ Database backward compatibility with automatic migrations  
✓ Password confirmation for sensitive admin operations  

---

## User Roles and Permissions

### Role 1: Admin (`admin`)

**Full System Access**

Permissions:
- ✓ Create, read, update, delete (CRUD) all reports
- ✓ View device passwords and WiFi/router credentials (plain text)
- ✓ Download all site data as CSV export (with no hidden fields)
- ✓ Approve new user registrations
- ✓ Access `/device_passwords` admin-only page

**Default Admin Account:**
```
Username:     admin
Email:        byamungutony@gmail.com
Password:     Mes@2026
Status:       Pre-verified (active on first run)
```

### Role 2: Technician (`technician`)

**Report Management Access Only**

Permissions:
- ✓ Create reports (all form fields)
- ✓ Edit and delete reports
- ✓ View report details
- ✓ Download reports as PDF
- ✗ View device passwords (displayed as `[HIDDEN]`)
- ✗ Access admin-only features
- ✗ View sensitive credentials in exports

**Default Technician Account:**
```
Username:     IT
Email:        byamungutony@gmail.com
Password:     Mes@2026
Status:       Pre-verified (active on first run)
```

**New Registrations:** All newly registered users automatically receive technician role.

---

## Default Accounts

Two accounts are automatically created on application first startup:

| Account Type | Username | Email | Password | Role | Status |
|--------------|----------|-------|----------|------|--------|
| **Admin** | `admin` | `byamungutony@gmail.com` | `Mes@2026` | admin | Verified ✓ |
| **IT Technician** | `IT` | `byamungutony@gmail.com` | `Mes@2026` | technician | Verified ✓ |

⚠️ **Important:** Change these default passwords immediately in production environments.

---

## Registration Process

### Complete Registration Flow

**Step 1: User Initiates Registration**
- Navigate to `/register`
- Fill registration form with:
  - `Username` (unique, 3-20 characters recommended)
  - `Email` (must be unique)
  - `Password` (minimum 6 characters)
  - `Confirm Password` (must match password)

**Step 2: Form Validation**
```
✓ Username must be provided and unique
✓ Email must be valid and unique
✓ Password must be at least 6 characters long
✓ Passwords match confirmation
✓ No duplicate usernames or emails allowed
```

**Step 3: Verification Code Generation**
- System generates random 6-digit code (example: `456789`)
- Code stored temporarily in database
- Auto-email sent to admin: `byamungutony@gmail.com`

**Step 4: Admin Receives Email**
```
Subject: New User Registration - Verification Code

A new user has registered with the following details:

Username: john_doe
Email: john@example.com
Verification Code: 456789

Please provide the verification code to the user to complete registration.
```

**Step 5: User Enters Verification Code**
- User navigates to `/verify` page
- User receives 6-digit code from administrator
- User enters code to activate account

**Step 6: Account Activation**
- System compares provided code with stored code
- If codes match:
  - Account marked as verified (`verified = 1`)
  - Verification code cleared from database
  - User can now log in
- If codes don't match:
  - Error message shown
  - User prompted to re-enter code

**Step 7: User Logs In**
- User returns to `/login`
- Enters username and password
- System verifies account is verified
- Session created with user info and role

---

## Email Verification

### How Email Verification Works

The system requires administrator approval via 6-digit verification code:

1. New user completes registration form
2. 6-digit verification code automatically generated
3. Email sent to administrator: `byamungutony@gmail.com`
4. Administrator manually communicates code to user
5. User enters code on `/verify` page to activate account
6. Verified users can then log in

### Email Configuration (Optional)

To enable automatic email sending, create `.env` file in project root:

```env
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

**Important Notes:**
- Use Gmail app password (NOT your regular Gmail password)
- Requires Gmail account with 2-factor authentication enabled
- Get app password: [Google Account Security](https://myaccount.google.com/apppasswords)

### Demo Mode (Without Email)

If SMTP credentials are not configured (no `.env` file):
- Registration process works normally
- 6-digit verification codes are still generated
- Administrator must manually share code with user
- System still requires code verification before login
- No automatic emails are sent

This allows complete testing without email server setup.

---

## Access Control

### Authentication Decorators

#### `@login_required`
Restricts route to authenticated users only. Redirects to login if not logged in.

```python
@app.route("/reports")
@login_required
def list_reports():
    # Only logged-in users can access
    return render_template("reports.html", reports=reports)
```

#### `@admin_required`
Restricts route to users with admin role. Must be used with `@login_required`.

```python
@app.route("/device_passwords")
@login_required
@admin_required
def view_device_passwords():
    # Only admins can access secrets
    return render_template("passwords.html")
```

#### `@technician_required`
Allows both admin and technician roles. Must be used with `@login_required`.

```python
@app.route("/report/new")
@login_required
@technician_required
def create_report():
    # Admins and technicians can create reports
    return render_template("new_report.html")
```

### Protected Routes Reference

| Route | Method | Login Required | Role | Purpose |
|-------|--------|----------------|------|---------|
| `/login` | GET, POST | No | - | User login |
| `/register` | GET, POST | No | - | New user registration |
| `/verify` | POST | No | - | Email verification code |
| `/logout` | GET | Yes | Any | Logout and clear session |
| `/` | GET | Yes | Any | Reports dashboard |
| `/report/new` | GET, POST | Yes | Any | Create new report |
| `/report/<id>` | GET | Yes | Any | View report details |
| `/report/<id>/edit` | GET, POST | Yes | Any | Edit existing report |
| `/report/<id>/delete` | POST | Yes | Any | Delete report |
| `/report/<id>/download` | GET | Yes | Any | Download report as PDF |
| `/download_all_csv` | GET | Yes | **Admin Only** | Export all reports to CSV |
| `/device_passwords` | GET, POST | Yes | **Admin Only** | View device/WiFi/router passwords |

---

## Security Features

### Password Hashing & Storage

**User Login Passwords:**
- Hashed using PBKDF2 algorithm (via Werkzeug)
- Minimum 6 characters required
- Password confirmation required during registration
- Never stored or displayed in plain text
- Verified using `check_password_hash()` on login attempts

**Device/WiFi/Router Passwords:**
- Stored in plain text in database (for admin access)
- Masked as `[HIDDEN]` in reports and CSV exports for non-admin users
- Fully visible only to admin users via `/device_passwords` page
- Requires admin password confirmation to view
- Admin password verified against hashed password in database

### Session Management

- Flask-Login manages all session creation and destruction
- Sessions automatically cleared on logout
- CSRF protection via Flask
- User data reloaded from database on each request
- Session tokens secure and httponly

### Database Security

- All SQL queries use parameterized statements (SQL injection prevention)
- User input validated before database storage
- Row-level security enforced via role-based decorators
- Password hashes are cryptographically secure (cannot be reversed)
- Database file stored in `instance/` folder

### Access Control Enforcement

- Role enforcement via Python decorators (applied at route level)
- Unauthorized access redirected to dashboard or login page
- Role verification happens on every protected request
- Admin-only routes require explicit admin role check

---

## Configuration

### Environment Variables (.env)

Optional file for email configuration. Create in project root:

```env
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

**Without .env:** System operates in demo mode (codes generated manually shared).  
**With .env:** Automatic email notifications to admin on registration.

### Database Schema

**Users Table:**

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,                    -- PBKDF2 hashed
    role TEXT NOT NULL DEFAULT 'technician',  -- 'admin' or 'technician'
    verified INTEGER DEFAULT 0,               -- 0 = pending, 1 = approved
    verification_code TEXT,                   -- 6-digit code (cleared after use)
    created_at TEXT NOT NULL
)
```

### Application Configuration

Settings in `app.py`:

```python
app.secret_key = "mes_report_app_secret_key_2026"  # Change this in production
ADMIN_EMAIL = "byamungutony@gmail.com"             # Admin email for notifications
```

---

## Protected Routes Detail

### Authentication Routes

#### POST `/login`
**Login with username and password**

Form:
```html
<form method="POST" action="/login">
    <input name="username" required>
    <input name="password" type="password" required>
    <button type="submit">Login</button>
</form>
```

Response:
- Success: Redirect to `/` (dashboard)
- Invalid credentials: Show error, stay on `/login`
- Unverified account: Show "pending verification" message

#### GET/POST `/register`
**Register new user account**

Form:
```html
<form method="POST" action="/register">
    <input name="username" required>
    <input name="email" type="email" required>
    <input name="password" type="password" required>
    <input name="confirm_password" type="password" required>
    <button type="submit">Register</button>
</form>
```

Response:
- Success: Redirect to `/verify` page
- Validation error: Show error message, stay on `/register`
- Duplicate user: Show "username or email exists" error

#### POST `/verify`
**Verify registration with 6-digit code**

Form:
```html
<form method="POST" action="/verify">
    <input name="username" type="hidden">
    <input name="email" type="hidden">
    <input name="verification_code" placeholder="000000" required>
    <button type="submit">Verify</button>
</form>
```

Response:
- Correct code: Redirect to `/login` with success message
- Incorrect code: Show error, return to verification form
- User not found: Redirect to `/register`

#### GET `/logout`
**Logout and destroy session**

- Clears all session data
- Redirects to `/login`
- Shows "logged out successfully" message

### Dashboard & Report Routes

#### GET `/`
**Report Dashboard**

- View filtered list of all reports
- Statistics and summaries
- Filter by site name, status, report type, priority
- Requires: `@login_required`

#### GET/POST `/report/new`
**Create New Report**

- Forms for all report fields
- Dynamic issue and device sections
- Requires: `@login_required`

#### GET `/report/<id>`
**View Report Details**

- Display complete report information
- Shows `[HIDDEN]` for passwords (non-admin users)
- Shows all device details for admin
- Requires: `@login_required`

#### GET/POST `/report/<id>/edit`
**Edit Report**

- Modify any report field
- Update dynamic sections
- Requires: `@login_required`

#### POST `/report/<id>/delete`
**Delete Report**

- Permanently remove report
- Requires: `@login_required`

#### GET `/report/<id>/download`
**Download Report as PDF**

- Generate formatted PDF
- Include logo and styling
- Requires: `@login_required`

### Admin-Only Routes

#### GET `/download_all_csv`
**Export All Reports to CSV**

- Export all site data
- No hidden or filtered fields
- Plain-text credentials included
- Requires: `@login_required` + `@admin_required`

#### GET/POST `/device_passwords`
**View All Device Credentials**

**Step 1 (GET):** Display password confirmation form

```html
<form method="POST">
    <input name="admin_password" type="password" placeholder="Enter admin password">
    <button type="submit">View Passwords</button>
</form>
```

**Step 2 (POST):** 
- Accept admin password input
- Verify against stored hashed admin password
- If correct: Display table with all device passwords
- If incorrect: Show error, return to form

Requires: `@login_required` + `@admin_required`

---

## User Object (Current User)

In routes and templates, `current_user` object is available:

```python
# In route handlers
current_user.id                # Integer user ID
current_user.username          # String username
current_user.email             # String email address
current_user.role              # String: 'admin' or 'technician'
current_user.is_authenticated  # Boolean: True if logged in

# In Jinja2 templates
{{ current_user.username }}
{{ current_user.role }}
{% if current_user.role == 'admin' %}
    Show admin-only content
{% endif %}
```

---

## Troubleshooting

### "Your account is pending verification"

**Problem:** User tries to log in before account is verified.

**Root Cause:** Administrator hasn't shared verification code yet.

**Solution:**
1. New user provides username to administrator
2. Administrator checks admin email (`byamungutony@gmail.com`) for 6-digit code
3. Administrator shares the code with user (message, email, Slack, etc.)
4. User enters code on `/verify` page
5. Account is activated
6. User can now log in

### Email verification code not received

**Problem:** No email notification when new user registers.

**Root Cause:** SMTP not configured (expected in demo mode).

**Solutions:**
- For demo mode: Use `/verify` page directly, ask admin for code manually
- For production: Configure `.env` file with `SENDER_EMAIL` and `SENDER_PASSWORD`
- Check database: View `users` table `verification_code` column directly

### Cannot access Device Passwords page

**Problem:** Redirect to dashboard when accessing `/device_passwords`.

**Root Cause:** User doesn't have admin role.

**Solution:**
- Log in with `admin` account (password: `Mes@2026`)
- Or request admin to share device credentials
- New registrations always get technician role

### Forgotten default admin password

**Problem:** Can't log in with default credentials.

**Solution:**
1. Delete database file: `instance/site_reports.db`
2. Restart application
3. Default accounts recreated:
   ```
   admin / Mes@2026 (admin role)
   IT / Mes@2026 (technician role)
   ```

⚠️ **WARNING:** This deletes all data. Only use for fresh start.

---

## Dependencies

All required packages in `requirements.txt`:

```
Flask==3.0.0
Flask-Login==0.6.2
reportlab==4.0.4
Werkzeug==3.0.0
python-dotenv==1.0.0
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Deployment (PythonAnywhere)

1. Upload entire `mes_report_generator` folder
2. Create new web app, select "Web framework: Flask"
3. Edit WSGI file to point to `wsgi.app`
4. Set `instance/` directory permissions to writable
5. Optional: Set environment variables in Web tab

---

## Production Checklist

- [ ] Change default `admin` password
- [ ] Change default `IT` password
- [ ] Change `app.secret_key` to random value
- [ ] Set `FLASK_ENV=production`
- [ ] Configure `.env` with SMTP credentials
- [ ] Enable HTTPS/SSL
- [ ] Set up automated backups
- [ ] Monitor logs for errors
- [ ] Review database security

---

## Support & Documentation

- Flask-Login: https://flask-login.readthedocs.io/
- Werkzeug Security: https://werkzeug.palletsprojects.com/
- Flask: https://flask.palletsprojects.com/

---

**Version:** 2.0 (Flask-Login Authentication System)  
**Last Updated:** February 20, 2026  
**Status:** Production Ready

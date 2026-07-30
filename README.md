# placement-portal-app

Placement portal web application for student placement purposes.  
A Flask-based campus recruitment management system for institutes, companies, and students.

## Tech Stack

- **Backend:** Flask 2.3.3
- **Frontend:** Jinja2, Bootstrap 5, HTML/CSS
- **Database:** SQLite (SQLAlchemy ORM)
- **Authentication:** Flask-Login

---

## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/24f2000019/placement-portal-app.git
cd placement-portal-app
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root folder:

```
SECRET_KEY=your_secret_key_here
```

You can generate a secret key by running this in Python:
```python
import secrets
print(secrets.token_hex(32))
```

### 5. Create the database

```bash
python create_db.py
```

This will create `instance/portal.db` with all the required tables.

### 6. Create the admin account

Run this once to set up the predefined admin user:

```python
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(
        email='admin@placement.edu',
        password=generate_password_hash('admin777'),
        role='admin',
        is_approved=True
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin created.")
```

Save this as `create_admin.py` and run `python create_admin.py`.

### 7. Run the application

```bash
python app.py
```

The app will be available at `http://127.0.0.1:5000`

---

## Default Login

| Role  | Email              | Password  |
|-------|--------------------|-----------|
| Admin | admin@placement.edu   | admin777  |

Companies and students can register from the home page.  
Company accounts need admin approval before they can log in.

---

## Folder Structure

```
placement-portal-app/
├── app.py                  # main Flask app and all routes
├── models.py               # SQLAlchemy database models
├── create_db.py            # script to initialise the database
├── create_admin.py         # script to create the admin user
├── requirements.txt        # Python dependencies
├── .env                    # secret key (not committed to git)
├── .gitignore
├── instance/
│   └── portal.db           # SQLite database (auto-created)
├── static/
│   ├── style.css
│   └── uploads/            # student resume uploads
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register_student.html
    ├── register_company.html
    ├── admin/
    │   ├── dashboard.html
    │   └── admin_student_view.html
    ├── company/
    │   ├── dashboard.html
    │   ├── create_drive.html
    │   ├── applications.html
    │   └── company_student_view.html
    └── student/
        ├── dashboard.html
        └── profile.html
```

---

## Notes

- Do not manually create or edit `portal.db` using DB Browser — the database must be created programmatically via `create_db.py`
- Resume uploads are stored in `static/uploads/` — this folder is excluded from git
- The `instance/` folder is also excluded from git

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
from app import app, db
from models import User, Student, Company, PlacementDrive, Application
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def create_database():
    with app.app_context():
        db.drop_all()

        db.create_all()
        print("Database tables created successfully")

        admin = User(
            email="admin@placement.edu",
            password=generate_password_hash("admin777"),
            role="admin",
            is_approved=True,
            is_blacklisted=False
        )
        db.session.add(admin)

        company_user = User(
            email="techcorp@example.com",
            password=generate_password_hash("company777"),
            role="company",
            is_approved=True,  
            is_blacklisted=False
        )
        db.session.add(company_user)
        db.session.flush() 

        company = Company(
            user_id=company_user.id,
            company_name="TechCorp Solutions",
            hr_name="John Smith",
            hr_phone="9876543210",
            website="<https://techcorp.com>",
            description="Leading IT services company"
        )
        db.session.add(company)
        db.session.flush()

        drive = PlacementDrive(
            company_id=company.id,
            job_title="Software Engineer Intern",
            job_description="Looking for passionate developers",
            eligibility_criteria="CGPA > 7.5, No backlogs",
            application_deadline=datetime.now() + timedelta(days=15),
            status="approved" 
        )
        db.session.add(drive)

        student_user = User(
            email="student@example.com",
            password=generate_password_hash("student777"),
            role="student",
            is_approved=True,
            is_blacklisted=False
        )
        db.session.add(student_user)
        db.session.flush()

        student = Student(
            user_id=student_user.id,
            name="Alice Johnson",
            roll_number="CS2024001",
            branch="Computer Science",
            year=3,
            cgpa=8.5,
            phone="9876543211"
        )
        db.session.add(student)

        db.session.commit()

        print("Sample data added successfully")
        print("\nLogin Credentials:")
        print("Admin - Email: admin@placement.edu | Password: admin777")
        print("Company - Email: techcorp@example.com | Password: company777")
        print("Student - Email: student@example.com | Password: student777")

if __name__ == "__main__":
    create_database()
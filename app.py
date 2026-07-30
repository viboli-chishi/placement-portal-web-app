from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

from models import db, User, Student, Company, PlacementDrive,Application, Notification
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'b4b8dc4a426b4a7bdd72ac2ba7349ff38c9c032131939f0f44ee5af28ee57520')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def notify_student(student_id, message):
    n = Notification(student_id=student_id, message=message)
    db.session.add(n)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            if user.is_blacklisted:
                flash('Your account has been blacklisted. Please contact admin.', 'danger')
                return redirect(url_for('login'))

            login_user(user)

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'company':
                if not user.is_approved:
                    flash('Your company registration is pending admin approval.', 'warning')
                    logout_user()
                    return redirect(url_for('login'))
                return redirect(url_for('company_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


#registration

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        branch = request.form.get('branch')
        year = request.form.get('year')
        cgpa = request.form.get('cgpa')
        phone = request.form.get('phone')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register_student'))

        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered.', 'danger')
            return redirect(url_for('register_student'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('register_student'))

        if not cgpa or not (0 <= float(cgpa) <= 10):
            flash('CGPA must be between 0 and 10.', 'danger')
            return redirect(url_for('register_student'))

        if not phone.isdigit() or len(phone) != 10:
            flash('Phone number must be 10 digits.', 'danger')
            return redirect(url_for('register_student'))

        user = User(email=email, password=generate_password_hash(password), role='student', is_approved=True)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            name=name,
            roll_number=roll_number,
            branch=branch,
            year=int(year),
            cgpa=float(cgpa),
            phone=phone
        )
        db.session.add(student)
        db.session.flush()

        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{roll_number}_{file.filename}")
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                student.resume_filename = filename

        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register_student.html')


@app.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        company_name = request.form.get('company_name')
        hr_name = request.form.get('hr_name')
        hr_phone = request.form.get('hr_phone')
        website = request.form.get('website')
        description = request.form.get('description')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register_company'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('register_company'))

        if not hr_phone.isdigit() or len(hr_phone) != 10:
            flash('Phone number must be 10 digits.', 'danger')
            return redirect(url_for('register_company'))
        
        user = User(email=email, password=generate_password_hash(password), role='company', is_approved=False)
        db.session.add(user)
        db.session.flush()

        company = Company(
            user_id=user.id,
            company_name=company_name,
            hr_name=hr_name,
            hr_phone=hr_phone,
            website=website,
            description=description
        )
        db.session.add(company)
        db.session.commit()

        flash('Registration submitted! Waiting for admin approval.', 'info')
        return redirect(url_for('login'))

    return render_template('register_company.html')


#studenroutes

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
 
    student = current_user.student_profile
 
    search_company = request.args.get('search_company', '').strip()
    search_position = request.args.get('search_position', '').strip()
    search_skills = request.args.get('search_skills', '').strip()
 
    drive_query = PlacementDrive.query.filter_by(status='approved')
 
    if search_company:
        drive_query = drive_query.join(Company).filter(
            Company.company_name.ilike(f'%{search_company}%')
        )
    if search_position:
        drive_query = drive_query.filter(
            PlacementDrive.job_title.ilike(f'%{search_position}%')
        )
    if search_skills:
        drive_query = drive_query.filter(
            db.or_(
                PlacementDrive.job_description.ilike(f'%{search_skills}%'),
                PlacementDrive.eligibility_criteria.ilike(f'%{search_skills}%')
            )
        )
 
    open_drives = drive_query.all()
    applications = Application.query.filter_by(student_id=student.id).all()
    applied_drive_ids = {app.drive_id for app in applications}
 
    unread_notifications = Notification.query.filter_by(
        student_id=student.id, is_read=False
    ).order_by(Notification.created_at.desc()).all()
 
    return render_template('student/dashboard.html',
        student=student,
        open_drives=open_drives,
        applications=applications,
        applied_drive_ids=applied_drive_ids,
        unread_notifications=unread_notifications,
        search_company=search_company,
        search_position=search_position,
        search_skills=search_skills
    )
 
@app.route('/student/notifications/read')
@login_required
def mark_notifications_read():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    student = current_user.student_profile
    Notification.query.filter_by(student_id=student.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('student_dashboard'))

@app.route('/student/apply/<int:drive_id>')
@login_required
def apply_drive(drive_id):
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    student = current_user.student_profile
    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.status != 'approved':
        flash('This drive is not available for applications.', 'danger')
        return redirect(url_for('student_dashboard'))

    already = Application.query.filter_by(student_id=student.id, drive_id=drive_id).first()
    if already:
        flash('You have already applied for this drive.', 'warning')
        return redirect(url_for('student_dashboard'))

    new_app = Application(student_id=student.id, drive_id=drive_id)
    db.session.add(new_app)
    db.session.commit()

    flash(f'Successfully applied for {drive.job_title}!', 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    student = current_user.student_profile

    if request.method == 'POST':
        student.phone = request.form.get('phone', student.phone)
        student.cgpa = float(request.form.get('cgpa', student.cgpa))
        student.year = int(request.form.get('year', student.year))
        student.branch = request.form.get('branch', student.branch)

        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{student.roll_number}_{file.filename}")
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                student.resume_filename = filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('student/profile.html', student=student)


#companyroutes

@app.route('/company/dashboard')
@login_required
def company_dashboard():
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    company = current_user.company_profile
    drives = PlacementDrive.query.filter_by(company_id=company.id).order_by(PlacementDrive.created_at.desc()).all()

    return render_template('company/dashboard.html', company=company, drives=drives)


@app.route('/company/drive/create', methods=['GET', 'POST'])
@login_required
def create_drive():
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        company = current_user.company_profile
        deadline_str = request.form.get('application_deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        if deadline <= datetime.now():
            flash('Deadline must be a future date.', 'danger')
            return redirect(url_for('create_drive'))
        drive = PlacementDrive(
            company_id=company.id,
            job_title=request.form.get('job_title'),
            job_description=request.form.get('job_description'),
            eligibility_criteria=request.form.get('eligibility_criteria'),
            salary=request.form.get('salary'),
            location=request.form.get('location'),
            application_deadline=deadline,
            status='pending' 
        )
        db.session.add(drive)
        db.session.commit()

        flash('Drive submitted for admin approval!', 'info')
        return redirect(url_for('company_dashboard'))

    return render_template('company/create_drive.html')


@app.route('/company/drive/<int:drive_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    drive = PlacementDrive.query.get_or_404(drive_id)

    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    if request.method == 'POST':
        drive.job_title = request.form.get('job_title')
        drive.job_description = request.form.get('job_description')
        drive.eligibility_criteria = request.form.get('eligibility_criteria')
        drive.salary = request.form.get('salary')
        drive.location = request.form.get('location')
        deadline_str = request.form.get('application_deadline')
        drive.application_deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')

        drive.status = 'pending'
        db.session.commit()
        flash('Drive updated. Pending re-approval from admin.', 'info')
        return redirect(url_for('company_dashboard'))

    return render_template('company/create_drive.html', drive=drive)


@app.route('/company/drive/<int:drive_id>/close')
@login_required
def close_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    drive.status = 'closed'
    db.session.commit()
    flash('Drive has been closed.', 'success')
    return redirect(url_for('company_dashboard'))


@app.route('/company/drive/<int:drive_id>/delete')
@login_required
def delete_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    db.session.delete(drive)
    db.session.commit()
    flash('Drive deleted.', 'success')
    return redirect(url_for('company_dashboard'))


@app.route('/company/drive/<int:drive_id>/applications')
@login_required
def drive_applications(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    applications = Application.query.filter_by(drive_id=drive_id).all()
    return render_template('company/applications.html', drive=drive, applications=applications)


@app.route('/company/application/<int:app_id>/update', methods=['POST'])
@login_required
def update_application_status(app_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
 
    application = Application.query.get_or_404(app_id)
    new_status = request.form.get('status')
    allowed_statuses = ['applied', 'shortlisted', 'selected', 'rejected','waitlisted']
 
    if new_status in allowed_statuses:
        old_status = application.status
        application.status = new_status
 
        if old_status != new_status:
            drive = application.drive
            msg = f"Your application for {drive.job_title} at {drive.company.company_name} is now: {new_status.capitalize()}"
            notify_student(application.student_id, msg)
 
        db.session.commit()
        flash('Status updated.', 'success')
 
    return redirect(url_for('drive_applications', drive_id=application.drive_id))
 
@app.route('/company/student/<int:student_id>')
@login_required
def view_student_profile(student_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
 
    student = Student.query.get_or_404(student_id)
    company = current_user.company_profile
 
    #only let company see students who applied to their drives
    applied = Application.query.join(PlacementDrive).filter(
        Application.student_id == student_id,
        PlacementDrive.company_id == company.id
    ).all()
 
    if not applied:
        flash("You can only view profiles of students who applied to your drives.", 'danger')
        return redirect(url_for('company_dashboard'))
 
    return render_template('company/student_view.html', student=student, applications=applied)

#adminroutes

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    student_search = request.args.get('student_search', '').strip()
    company_search = request.args.get('company_search', '').strip()

    student_query = Student.query
    if student_search:
        student_query = student_query.filter(
            db.or_(
                Student.name.ilike(f'%{student_search}%'),
                Student.roll_number.ilike(f'%{student_search}%'),
                Student.phone.ilike(f'%{student_search}%')
            )
        )
    students = student_query.all()

    company_query = Company.query
    if company_search:
        company_query = company_query.filter(
            Company.company_name.ilike(f'%{company_search}%')
        )
    companies = company_query.all()

    all_drives = PlacementDrive.query.order_by(PlacementDrive.created_at.desc()).all()
    all_applications = Application.query.all()

    total_students = Student.query.count()
    approved_companies = sum(1 for c in Company.query.all() if c.user.is_approved and not c.user.is_blacklisted)
    pending_companies = sum(1 for c in Company.query.all() if not c.user.is_approved and not c.user.is_blacklisted)
    pending_drives = PlacementDrive.query.filter_by(status='pending').count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()

    return render_template('admin/dashboard.html',
        students=students,
        companies=companies,
        all_drives=all_drives,
        all_applications=all_applications,
        total_students=total_students,
        approved_companies=approved_companies,
        pending_companies=pending_companies,
        pending_drives=pending_drives,
        total_drives=total_drives,
        total_applications=total_applications,
        student_search=student_search,
        company_search=company_search
    )

@app.route('/admin/student/<int:student_id>')
@login_required
def admin_view_student(student_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
 
    student = Student.query.get_or_404(student_id)
    applications = Application.query.filter_by(student_id=student_id).all()
    return render_template('admin/admin_student_view.html', student=student, applications=applications)

@app.route('/admin/company/<int:company_id>/approve')
@login_required
def approve_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    company = Company.query.get_or_404(company_id)
    company.user.is_approved = True
    db.session.commit()
    flash(f'{company.company_name} approved.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/company/<int:company_id>/reject')
@login_required
def reject_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    company = Company.query.get_or_404(company_id)
    company.user.is_approved = False
    company.user.is_blacklisted = True
    db.session.commit()
    flash(f'{company.company_name} rejected.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/drive/<int:drive_id>/approve')
@login_required
def approve_drive(drive_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'approved'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" approved.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/drive/<int:drive_id>/reject')
@login_required
def reject_drive(drive_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'rejected'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" rejected.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/user/<int:user_id>/blacklist')
@login_required
def blacklist_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.is_blacklisted = True

    if user.role == 'company' and user.company_profile:
        for drive in user.company_profile.drives:
            if drive.status in ('pending', 'approved'):
                drive.status = 'closed'

    db.session.commit()
    flash('User blacklisted.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/user/<int:user_id>/unblacklist')
@login_required
def unblacklist_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.is_blacklisted = False
    if user.role == 'company':
        user.is_approved = True
    db.session.commit()
    flash('User reactivated.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/student/<int:student_id>/delete')
@login_required
def delete_student(student_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    student = Student.query.get_or_404(student_id)
    db.session.delete(student.user)
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/company/<int:company_id>/delete')
@login_required
def delete_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    company = Company.query.get_or_404(company_id)
    db.session.delete(company.user)
    db.session.commit()
    flash('Company deleted.', 'success')
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    app.run(debug=True)
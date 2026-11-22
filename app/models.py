from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class College(db.Model):
    __tablename__ = 'colleges'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    address = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contact_number = db.Column(db.String(50), nullable=False)
    logo_filename = db.Column(db.String(255), default='default_college_logo.png')
    email_domain = db.Column(db.String(100), default='college.edu', nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)  # active, pending, deactivated
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship('User', back_populates='college', cascade='all, delete-orphan')
    courses = db.relationship('Course', back_populates='college', cascade='all, delete-orphan')
    branches = db.relationship('Branch', back_populates='college', cascade='all, delete-orphan')
    subjects = db.relationship('Subject', back_populates='college', cascade='all, delete-orphan')
    examinations = db.relationship('Examination', back_populates='college', cascade='all, delete-orphan')
    students = db.relationship('StudentProfile', back_populates='college', cascade='all, delete-orphan')
    faculty = db.relationship('FacultyProfile', back_populates='college', cascade='all, delete-orphan')
    administrators = db.relationship('CollegeAdminProfile', back_populates='college', cascade='all, delete-orphan')
    admin_profiles = db.relationship('AdminProfile', back_populates='college', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<College {self.code}: {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # super_admin, college_admin, faculty, student
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    mobile_number = db.Column(db.String(30), nullable=True)
    phone_number = db.Column(db.String(30), nullable=True)
    registration_status = db.Column(db.String(30), default='active', nullable=False)  # active, pending_approval, pending_verification, approved, rejected, deactivated
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    last_login_date = db.Column(db.DateTime, nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    demo_session_id = db.Column(db.String(100), nullable=True)
    account_type = db.Column(db.String(30), default='standard', nullable=False)  # standard, demo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    college = db.relationship('College', back_populates='users')
    student_profile = db.relationship('StudentProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    faculty_profile = db.relationship('FacultyProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    college_admin_profile = db.relationship('CollegeAdminProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    admin_profile = db.relationship('AdminProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def record_login(self):
        self.last_login_date = datetime.utcnow()
        db.session.commit()

    @property
    def phone(self):
        return self.phone_number or self.mobile_number

    @property
    def is_active_and_approved(self):
        return self.is_active and self.registration_status in ('active', 'approved')

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    @property
    def is_college_admin(self):
        return self.role == 'college_admin'

    @property
    def is_faculty(self):
        return self.role == 'faculty'

    @property
    def is_student(self):
        return self.role == 'student'

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User {self.identifier} ({self.role})>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    duration_years = db.Column(db.Integer, default=4, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('college_id', 'code', name='uix_college_course_code'),
    )

    college = db.relationship('College', back_populates='courses')
    branches = db.relationship('Branch', back_populates='course', cascade='all, delete-orphan')
    subjects = db.relationship('Subject', back_populates='course', cascade='all, delete-orphan')
    students = db.relationship('StudentProfile', back_populates='course')

    def __repr__(self):
        return f'<Course {self.code}: {self.name}>'


class Branch(db.Model):
    __tablename__ = 'branches'

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('college_id', 'course_id', 'code', name='uix_college_branch_code'),
    )

    college = db.relationship('College', back_populates='branches')
    course = db.relationship('Course', back_populates='branches')
    subjects = db.relationship('Subject', back_populates='branch', cascade='all, delete-orphan')
    students = db.relationship('StudentProfile', back_populates='branch')

    def __repr__(self):
        return f'<Branch {self.code}: {self.name}>'


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    academic_year = db.Column(db.String(20), default='2026-2027')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('college_id', 'branch_id', 'semester', 'code', name='uix_college_subject_code'),
    )

    college = db.relationship('College', back_populates='subjects')
    course = db.relationship('Course', back_populates='subjects')
    branch = db.relationship('Branch', back_populates='subjects')
    examinations = db.relationship('Examination', back_populates='subject', cascade='all, delete-orphan')
    faculty_assignments = db.relationship('FacultySubjectAssignment', back_populates='subject', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Subject {self.code}: {self.name}>'


class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    registration_number = db.Column(db.String(80), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='RESTRICT'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='RESTRICT'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), nullable=False, default='2026-2027')
    contact_number = db.Column(db.String(50), nullable=True)
    registration_status = db.Column(db.String(30), default='active', nullable=False)

    user = db.relationship('User', back_populates='student_profile')
    college = db.relationship('College', back_populates='students')
    course = db.relationship('Course', back_populates='students')
    branch = db.relationship('Branch', back_populates='students')
    attempts = db.relationship('ExamAttempt', back_populates='student', cascade='all, delete-orphan')
    results = db.relationship('ExamResult', back_populates='student', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __repr__(self):
        return f'<Student {self.registration_number}: {self.full_name}>'


class FacultyProfile(db.Model):
    __tablename__ = 'faculty_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    faculty_id_code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    designation = db.Column(db.String(100), default='Assistant Professor')
    department_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(50), nullable=True)
    registration_status = db.Column(db.String(30), default='active', nullable=False)

    user = db.relationship('User', back_populates='faculty_profile')
    college = db.relationship('College', back_populates='faculty')
    examinations = db.relationship('Examination', back_populates='faculty', cascade='all, delete-orphan')
    assignments = db.relationship('FacultySubjectAssignment', back_populates='faculty', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def phone_number(self):
        return self.contact_number

    def __repr__(self):
        return f'<Faculty {self.faculty_id_code}: {self.full_name}>'


class CollegeAdminProfile(db.Model):
    __tablename__ = 'college_admin_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    admin_id_code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    contact_number = db.Column(db.String(50), nullable=True)
    registration_status = db.Column(db.String(30), default='active', nullable=False)

    user = db.relationship('User', back_populates='college_admin_profile')
    college = db.relationship('College', back_populates='administrators')

    @property
    def phone_number(self):
        return self.contact_number

    def __repr__(self):
        return f'<CollegeAdmin {self.admin_id_code}: {self.full_name}>'


class AdminProfile(db.Model):
    __tablename__ = 'admin_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    admin_id_code = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=True)
    contact_number = db.Column(db.String(50), nullable=True)
    registration_status = db.Column(db.String(30), default='active', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='admin_profile')
    college = db.relationship('College', back_populates='admin_profiles')

    @property
    def phone_number(self):
        return self.contact_number

    def __repr__(self):
        return f'<AdminProfile {self.admin_id_code}: {self.full_name}>'


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('password_reset_tokens', cascade='all, delete-orphan'))

    @property
    def is_valid(self):
        return self.used_at is None and datetime.utcnow() <= self.expires_at

    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id} valid={self.is_valid}>'


class AccountVerification(db.Model):
    __tablename__ = 'account_verifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    requested_role = db.Column(db.String(30), nullable=False)  # student, faculty, college_admin
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=True)
    status = db.Column(db.String(30), default='pending_approval', nullable=False)  # pending_approval, approved, rejected
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('verifications', cascade='all, delete-orphan'))
    college = db.relationship('College')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f'<AccountVerification user_id={self.user_id} role={self.requested_role} status={self.status}>'


class FacultySubjectAssignment(db.Model):
    __tablename__ = 'faculty_subject_assignments'

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty_profiles.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('faculty_id', 'subject_id', name='uix_faculty_subject'),
    )

    faculty = db.relationship('FacultyProfile', back_populates='assignments')
    subject = db.relationship('Subject', back_populates='faculty_assignments')


class Examination(db.Model):
    __tablename__ = 'examinations'

    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty_profiles.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    total_marks = db.Column(db.Float, default=0.0)
    passing_percentage = db.Column(db.Float, default=40.0)
    max_attempts = db.Column(db.Integer, default=1)
    negative_marking = db.Column(db.Boolean, default=False)
    negative_mark_value = db.Column(db.Float, default=0.25)
    status = db.Column(db.String(30), default='draft')  # draft, scheduled, active, completed, cancelled
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    college = db.relationship('College', back_populates='examinations')
    faculty = db.relationship('FacultyProfile', back_populates='examinations')
    course = db.relationship('Course')
    branch = db.relationship('Branch')
    subject = db.relationship('Subject', back_populates='examinations')
    questions = db.relationship('Question', back_populates='examination', cascade='all, delete-orphan', order_by='Question.question_number')
    attempts = db.relationship('ExamAttempt', back_populates='examination', cascade='all, delete-orphan')
    results = db.relationship('ExamResult', back_populates='examination', cascade='all, delete-orphan')

    @property
    def question_count(self):
        return len(self.questions)

    def calculate_total_marks(self):
        total = sum(q.marks for q in self.questions)
        self.total_marks = total
        return total

    def __repr__(self):
        return f'<Examination {self.id}: {self.title} ({self.status})>'


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Float, default=1.0, nullable=False)
    negative_marks = db.Column(db.Float, default=0.0, nullable=False)
    explanation = db.Column(db.Text, nullable=True)

    examination = db.relationship('Examination', back_populates='questions')
    options = db.relationship('Option', back_populates='question', cascade='all, delete-orphan', order_by='Option.option_number')

    def __repr__(self):
        return f'<Question {self.question_number} (Exam {self.examination_id})>'


class Option(db.Model):
    __tablename__ = 'options'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    option_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)

    question = db.relationship('Question', back_populates='options')

    def __repr__(self):
        return f'<Option {self.option_number} (Q{self.question_id}): correct={self.is_correct}>'


class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    attempt_number = db.Column(db.Integer, default=1, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), default='in_progress', nullable=False)  # in_progress, submitted, timed_out, cancelled
    ip_address = db.Column(db.String(50), nullable=True)
    tab_switch_count = db.Column(db.Integer, default=0, nullable=False)
    fullscreen_exit_count = db.Column(db.Integer, default=0, nullable=False)

    student = db.relationship('StudentProfile', back_populates='attempts')
    examination = db.relationship('Examination', back_populates='attempts')
    answers = db.relationship('StudentAnswer', back_populates='attempt', cascade='all, delete-orphan')
    result = db.relationship('ExamResult', back_populates='attempt', uselist=False, cascade='all, delete-orphan')
    activity_logs = db.relationship('ExamActivityLog', back_populates='attempt', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ExamAttempt {self.id} Student={self.student_id} Exam={self.examination_id} Status={self.status}>'


class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('options.id', ondelete='SET NULL'), nullable=True)
    is_marked_for_review = db.Column(db.Boolean, default=False, nullable=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('attempt_id', 'question_id', name='uix_attempt_question'),
    )

    attempt = db.relationship('ExamAttempt', back_populates='answers')
    question = db.relationship('Question')
    selected_option = db.relationship('Option')


class ExamResult(db.Model):
    __tablename__ = 'exam_results'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), unique=True, nullable=False)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    wrong_answers = db.Column(db.Integer, nullable=False)
    unanswered_questions = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Float, nullable=False)
    obtained_marks = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    is_passed = db.Column(db.Boolean, nullable=False)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    attempt = db.relationship('ExamAttempt', back_populates='result')
    examination = db.relationship('Examination', back_populates='results')
    student = db.relationship('StudentProfile', back_populates='results')
    college = db.relationship('College')

    def __repr__(self):
        return f'<ExamResult {self.id}: Student {self.student_id} Score {self.obtained_marks}/{self.total_marks} ({self.percentage}%)>'


class ExamActivityLog(db.Model):
    __tablename__ = 'exam_activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id', ondelete='CASCADE'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    event_data = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    attempt = db.relationship('ExamAttempt', back_populates='activity_logs')

    def __repr__(self):
        return f'<ExamActivityLog {self.event_type} at {self.timestamp}>'

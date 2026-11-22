import secrets
from datetime import datetime, date, time, timedelta
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, CollegeAdminProfile, AdminProfile,
    Course, Branch, Subject, Examination, Question, Option, ExamAttempt,
    StudentAnswer, ExamResult, FacultySubjectAssignment, ExamActivityLog
)


def get_or_create_demo_college(custom_name=None):
    """
    Finds or provisions the isolated Demo College.
    Guarantees strict tenant isolation: Demo records never mix with production colleges.
    """
    demo_college = College.query.filter_by(code='DEMO-TECH').first()
    if not demo_college:
        demo_college = College(
            name=custom_name or 'Demo Institute of Technology & Science',
            code='DEMO-TECH',
            address='100 Innovation Boulevard, Cyber Tech Park, University City',
            email='admin@demotech.edu',
            contact_number='+91 40 5555 0199',
            logo_filename='default_college_logo.png',
            email_domain='demotech.edu',
            status='active',
            is_demo=True
        )
        db.session.add(demo_college)
        db.session.flush()

    ensure_demo_curriculum_and_exams(demo_college)
    return demo_college


def ensure_demo_curriculum_and_exams(demo_college):
    """
    Sets up courses, branches, subjects, questions, and baseline cohort
    for a rich, interactive demonstration experience.
    """
    # 1. Course: B.Tech
    course = Course.query.filter_by(college_id=demo_college.id, code='BTECH').first()
    if not course:
        course = Course(
            college_id=demo_college.id,
            code='BTECH',
            name='Bachelor of Technology',
            duration_years=4
        )
        db.session.add(course)
        db.session.flush()

    # 2. Branches: CSE & AIDS
    branch_cse = Branch.query.filter_by(college_id=demo_college.id, code='CSE').first()
    if not branch_cse:
        branch_cse = Branch(
            college_id=demo_college.id,
            course_id=course.id,
            code='CSE',
            name='Computer Science & Engineering'
        )
        db.session.add(branch_cse)
        db.session.flush()

    branch_aids = Branch.query.filter_by(college_id=demo_college.id, code='AIDS').first()
    if not branch_aids:
        branch_aids = Branch(
            college_id=demo_college.id,
            course_id=course.id,
            code='AIDS',
            name='Artificial Intelligence & Data Science'
        )
        db.session.add(branch_aids)
        db.session.flush()

    # 3. Semester 5 CSE Subjects
    subject_dbms = Subject.query.filter_by(college_id=demo_college.id, code='CS501').first()
    if not subject_dbms:
        subject_dbms = Subject(
            college_id=demo_college.id,
            course_id=course.id,
            branch_id=branch_cse.id,
            semester=5,
            code='CS501',
            name='Database Management Systems & Cloud Architecture',
            academic_year='2026-2027'
        )
        subject_os = Subject(
            college_id=demo_college.id,
            course_id=course.id,
            branch_id=branch_cse.id,
            semester=5,
            code='CS502',
            name='Operating Systems & Virtualization',
            academic_year='2026-2027'
        )
        subject_cn = Subject(
            college_id=demo_college.id,
            course_id=course.id,
            branch_id=branch_cse.id,
            semester=5,
            code='CS503',
            name='Computer Networks & Distributed Systems',
            academic_year='2026-2027'
        )
        db.session.add_all([subject_dbms, subject_os, subject_cn])
        db.session.flush()

    # 4. Default Demo Faculty Examiner if none exists yet
    default_fac_profile = FacultyProfile.query.filter_by(college_id=demo_college.id).first()
    if not default_fac_profile:
        fac_user = User(
            identifier='FAC-DEMO-EXAM',
            email='examiner@demotech.edu',
            role='faculty',
            college_id=demo_college.id,
            is_active=True,
            registration_status='approved',
            is_demo=True,
            account_type='demo'
        )
        fac_user.set_password('DemoFaculty@123')
        db.session.add(fac_user)
        db.session.flush()

        default_fac_profile = FacultyProfile(
            user_id=fac_user.id,
            faculty_id_code='FAC-DEMO-EXAM',
            first_name='Dr. Vikram',
            last_name='Nambiar',
            college_id=demo_college.id,
            designation='Head of Department & Chief Examiner',
            department_name='Computer Science & Engineering',
            registration_status='approved'
        )
        db.session.add(default_fac_profile)
        db.session.flush()

    # Ensure faculty subject assignment
    assign = FacultySubjectAssignment.query.filter_by(
        faculty_id=default_fac_profile.id,
        subject_id=subject_dbms.id
    ).first()
    if not assign:
        db.session.add(FacultySubjectAssignment(
            college_id=demo_college.id,
            faculty_id=default_fac_profile.id,
            subject_id=subject_dbms.id
        ))
        db.session.flush()

    # 5. Interactive Demo Examination
    today = date.today()
    demo_exam = Examination.query.filter_by(college_id=demo_college.id, is_demo=True).first()
    if not demo_exam:
        demo_exam = Examination(
            college_id=demo_college.id,
            faculty_id=default_fac_profile.id,
            course_id=course.id,
            branch_id=branch_cse.id,
            semester=5,
            subject_id=subject_dbms.id,
            title='Demo Mid-Term Examination: Database Systems & Cloud Architecture',
            instructions='Demonstration Examination for Academic Evaluation. Answer all 5 questions. Real-time autograding, ranking, and attendance reports are generated upon submission.',
            exam_date=today,
            start_time=time(0, 0),
            end_time=time(23, 59),
            duration_minutes=45,
            total_marks=10.0,
            passing_percentage=40.0,
            max_attempts=3,
            status='active',
            is_demo=True
        )
        db.session.add(demo_exam)
        db.session.flush()

        # Questions & Options
        q1 = Question(
            examination_id=demo_exam.id,
            question_number=1,
            question_text='Which relational algebra operation represents a Cartesian product immediately followed by a selection condition?',
            marks=2.0,
            negative_marks=0.0,
            explanation='A Theta Join (or equijoin) is mathematically defined as a selection applied over a Cartesian cross product.'
        )
        db.session.add(q1)
        db.session.flush()
        db.session.add_all([
            Option(question_id=q1.id, option_number=1, option_text='Projection', is_correct=False),
            Option(question_id=q1.id, option_number=2, option_text='Theta Join', is_correct=True),
            Option(question_id=q1.id, option_number=3, option_text='Natural Union', is_correct=False),
            Option(question_id=q1.id, option_number=4, option_text='Relational Division', is_correct=False),
        ])

        q2 = Question(
            examination_id=demo_exam.id,
            question_number=2,
            question_text='In database ACID transaction guarantees, what does the Isolation property ensure?',
            marks=2.0,
            negative_marks=0.0,
            explanation='Isolation ensures that concurrent execution of transactions leaves the database in the same state that would have been obtained if transactions were executed sequentially.'
        )
        db.session.add(q2)
        db.session.flush()
        db.session.add_all([
            Option(question_id=q2.id, option_number=1, option_text='Immediate disk persistence without buffer flushing', is_correct=False),
            Option(question_id=q2.id, option_number=2, option_text='Concurrent transactions execute without uncommitted interference', is_correct=True),
            Option(question_id=q2.id, option_number=3, option_text='Atomic rollback upon primary key collision', is_correct=False),
            Option(question_id=q2.id, option_number=4, option_text='Cryptographic hashing of table files', is_correct=False),
        ])

        q3 = Question(
            examination_id=demo_exam.id,
            question_number=3,
            question_text='Which database normal form strictly eliminates transitive dependencies on non-prime attributes?',
            marks=2.0,
            negative_marks=0.0,
            explanation='Third Normal Form (3NF) requires 2NF plus no non-prime attribute should be transitively dependent on any candidate key.'
        )
        db.session.add(q3)
        db.session.flush()
        db.session.add_all([
            Option(question_id=q3.id, option_number=1, option_text='First Normal Form (1NF)', is_correct=False),
            Option(question_id=q3.id, option_number=2, option_text='Second Normal Form (2NF)', is_correct=False),
            Option(question_id=q3.id, option_number=3, option_text='Third Normal Form (3NF)', is_correct=True),
            Option(question_id=q3.id, option_number=4, option_text='Fifth Normal Form (5NF)', is_correct=False),
        ])

        q4 = Question(
            examination_id=demo_exam.id,
            question_number=4,
            question_text='Which balanced index tree structure is industry-standard in relational database storage engines for efficient range queries?',
            marks=2.0,
            negative_marks=0.0,
            explanation='B+ Trees link leaf nodes sequentially in a doubly-linked list, allowing high-performance sequential range scanning.'
        )
        db.session.add(q4)
        db.session.flush()
        db.session.add_all([
            Option(question_id=q4.id, option_number=1, option_text='Inverted Token Map', is_correct=False),
            Option(question_id=q4.id, option_number=2, option_text='B+ Tree', is_correct=True),
            Option(question_id=q4.id, option_number=3, option_text='Red-Black Binary Tree', is_correct=False),
            Option(question_id=q4.id, option_number=4, option_text='Hash Directory', is_correct=False),
        ])

        q5 = Question(
            examination_id=demo_exam.id,
            question_number=5,
            question_text='Which consensus protocol is standardly used to ensure atomic multi-node commits across distributed database clusters?',
            marks=2.0,
            negative_marks=0.0,
            explanation='Two-Phase Commit (2PC) coordinates across participating nodes through a prepare phase followed by a commit/abort phase.'
        )
        db.session.add(q5)
        db.session.flush()
        db.session.add_all([
            Option(question_id=q5.id, option_number=1, option_text='Two-Phase Commit (2PC)', is_correct=True),
            Option(question_id=q5.id, option_number=2, option_text='Bellman-Ford Distance Vector', is_correct=False),
            Option(question_id=q5.id, option_number=3, option_text='Sliding Window ARQ', is_correct=False),
            Option(question_id=q5.id, option_number=4, option_text='Token Ring Arbitration', is_correct=False),
        ])
        db.session.flush()

    # Ensure demo exam is always active today for smooth demo execution
    if demo_exam.exam_date != today:
        demo_exam.exam_date = today
        demo_exam.status = 'active'
        db.session.flush()

    # 6. Baseline Demo Cohort (Priya Sharma, Rahul Varma, Ananya Rao)
    # Provides realistic peer records for attendance reports & rankings
    cohort_specs = [
        ('DEMO-CSE-001', 'priya.demo@demotech.edu', 'Priya', 'Sharma', True, 8.0),
        ('DEMO-CSE-002', 'rahul.demo@demotech.edu', 'Rahul', 'Varma', True, 6.0),
        ('DEMO-CSE-003', 'ananya.demo@demotech.edu', 'Ananya', 'Rao', False, 0.0),
    ]

    for roll, mail, fn, ln, attended, score in cohort_specs:
        st_u = User.query.filter_by(email=mail).first()
        if not st_u:
            st_u = User(
                identifier=roll,
                email=mail,
                role='student',
                college_id=demo_college.id,
                is_active=True,
                registration_status='approved',
                is_demo=True,
                account_type='demo'
            )
            st_u.set_password('DemoStudent@123')
            db.session.add(st_u)
            db.session.flush()

            st_p = StudentProfile(
                user_id=st_u.id,
                registration_number=roll,
                first_name=fn,
                last_name=ln,
                college_id=demo_college.id,
                course_id=course.id,
                branch_id=branch_cse.id,
                semester=5,
                academic_year='2026-2027',
                registration_status='approved'
            )
            db.session.add(st_p)
            db.session.flush()

            if attended and demo_exam:
                att = ExamAttempt(
                    examination_id=demo_exam.id,
                    student_id=st_p.id,
                    college_id=demo_college.id,
                    attempt_number=1,
                    start_time=datetime.utcnow() - timedelta(hours=2),
                    end_time=datetime.utcnow() - timedelta(hours=1, minutes=20),
                    status='submitted'
                )
                db.session.add(att)
                db.session.flush()

                passed = score >= 4.0
                res = ExamResult(
                    attempt_id=att.id,
                    examination_id=demo_exam.id,
                    student_id=st_p.id,
                    college_id=demo_college.id,
                    total_questions=5,
                    correct_answers=int(score / 2.0),
                    wrong_answers=5 - int(score / 2.0),
                    unanswered_questions=0,
                    total_marks=10.0,
                    obtained_marks=score,
                    percentage=(score / 10.0) * 100.0,
                    is_passed=passed
                )
                db.session.add(res)
                db.session.flush()

    db.session.commit()


def authenticate_demo_student(name, email, roll_number, college_name=None, branch_name=None, password=None):
    """
    Creates or retrieves a demo student account and associates with demo curriculum.
    Guarantees isolation: rejects emails or roll numbers registered to production accounts.
    """
    name = (name or '').strip()
    email = (email or '').strip().lower()
    roll_number = (roll_number or '').strip().upper()
    password = password.strip() if password else 'Demo@123'

    if not name:
        name = 'Demo Candidate'
    if not email:
        email = f"demo.student.{secrets.token_hex(4)}@demotech.edu"
    if not roll_number:
        roll_number = f"DEMO-{secrets.token_hex(3).upper()}"

    # Check collision with real production accounts
    existing_real_user = User.query.filter(
        (User.email == email) | (User.identifier == roll_number)
    ).first()
    if existing_real_user and not existing_real_user.is_demo:
        return None, 'This email or roll number belongs to a registered production account. Please use Normal Login Mode.'

    demo_college = get_or_create_demo_college(college_name)
    course = Course.query.filter_by(college_id=demo_college.id, code='BTECH').first()
    branch = Branch.query.filter_by(college_id=demo_college.id, code='CSE').first()
    if branch_name and branch_name.upper() in ('ECE', 'ELECTRONICS'):
        branch = Branch.query.filter_by(college_id=demo_college.id, code='ECE').first() or branch

    # Check existing demo account
    demo_user = User.query.filter(
        (User.email == email) | (User.identifier == roll_number)
    ).first()

    if demo_user and demo_user.is_demo:
        # Update session / password if requested
        demo_user.set_password(password)
        demo_user.demo_session_id = secrets.token_hex(16)
        demo_user.last_login_date = datetime.utcnow()
        demo_user.is_active = True
        demo_user.registration_status = 'approved'
        db.session.commit()
        return demo_user, None

    # Create new demo student
    parts = name.split(maxsplit=1)
    fn = parts[0]
    ln = parts[1] if len(parts) > 1 else 'Candidate'

    demo_user = User(
        identifier=roll_number,
        email=email,
        role='student',
        college_id=demo_college.id,
        is_active=True,
        registration_status='approved',
        is_demo=True,
        account_type='demo',
        demo_session_id=secrets.token_hex(16),
        last_login_date=datetime.utcnow()
    )
    demo_user.set_password(password)
    db.session.add(demo_user)
    db.session.flush()

    student_profile = StudentProfile(
        user_id=demo_user.id,
        registration_number=roll_number,
        first_name=fn,
        last_name=ln,
        college_id=demo_college.id,
        course_id=course.id,
        branch_id=branch.id,
        semester=5,
        academic_year='2026-2027',
        registration_status='approved'
    )
    db.session.add(student_profile)
    db.session.commit()

    return demo_user, None


def authenticate_demo_faculty(name, email, faculty_id, college_name=None, department_name=None, password=None):
    """
    Creates or retrieves a demo faculty account and connects with demo examinations.
    """
    name = (name or '').strip()
    email = (email or '').strip().lower()
    faculty_id = (faculty_id or '').strip().upper()
    password = password.strip() if password else 'Demo@123'
    dept = department_name.strip() if department_name else 'Computer Science & Engineering'

    if not name:
        name = 'Demo Professor'
    if not email:
        email = f"demo.faculty.{secrets.token_hex(4)}@demotech.edu"
    if not faculty_id:
        faculty_id = f"FAC-DEMO-{secrets.token_hex(3).upper()}"

    # Check collision with real production accounts
    existing_real_user = User.query.filter(
        (User.email == email) | (User.identifier == faculty_id)
    ).first()
    if existing_real_user and not existing_real_user.is_demo:
        return None, 'This email or faculty ID belongs to a registered production account. Please use Normal Login Mode.'

    demo_college = get_or_create_demo_college(college_name)

    # Check existing demo account
    demo_user = User.query.filter(
        (User.email == email) | (User.identifier == faculty_id)
    ).first()

    if demo_user and demo_user.is_demo:
        demo_user.set_password(password)
        demo_user.demo_session_id = secrets.token_hex(16)
        demo_user.last_login_date = datetime.utcnow()
        demo_user.is_active = True
        demo_user.registration_status = 'approved'
        db.session.commit()
        return demo_user, None

    # Create new demo faculty
    parts = name.split(maxsplit=1)
    fn = parts[0]
    ln = parts[1] if len(parts) > 1 else 'Faculty'

    demo_user = User(
        identifier=faculty_id,
        email=email,
        role='faculty',
        college_id=demo_college.id,
        is_active=True,
        registration_status='approved',
        is_demo=True,
        account_type='demo',
        demo_session_id=secrets.token_hex(16),
        last_login_date=datetime.utcnow()
    )
    demo_user.set_password(password)
    db.session.add(demo_user)
    db.session.flush()

    faculty_profile = FacultyProfile(
        user_id=demo_user.id,
        faculty_id_code=faculty_id,
        first_name=fn,
        last_name=ln,
        college_id=demo_college.id,
        designation='Associate Professor (Demo Evaluator)',
        department_name=dept,
        registration_status='approved'
    )
    db.session.add(faculty_profile)
    db.session.flush()

    # Assign all demo subjects to this faculty for rich dashboard access
    subjects = Subject.query.filter_by(college_id=demo_college.id).all()
    for sub in subjects:
        existing_assign = FacultySubjectAssignment.query.filter_by(
            faculty_id=faculty_profile.id,
            subject_id=sub.id
        ).first()
        if not existing_assign:
            db.session.add(FacultySubjectAssignment(
                college_id=demo_college.id,
                faculty_id=faculty_profile.id,
                subject_id=sub.id
            ))

    # Link demo examinations to this faculty profile so reports display immediately
    demo_exams = Examination.query.filter_by(college_id=demo_college.id, is_demo=True).all()
    for exam in demo_exams:
        exam.faculty_id = faculty_profile.id

    db.session.commit()
    return demo_user, None


def authenticate_demo_college_admin(name, email, college_name=None, admin_id=None, password=None):
    """
    Creates or retrieves a demo college admin account, restricted to the demo college.
    """
    name = (name or '').strip()
    email = (email or '').strip().lower()
    admin_id = (admin_id or '').strip().upper()
    password = password.strip() if password else 'Demo@123'

    if not name:
        name = 'Demo Administrator'
    if not email:
        email = f"demo.admin.{secrets.token_hex(4)}@demotech.edu"
    if not admin_id:
        admin_id = f"ADM-DEMO-{secrets.token_hex(3).upper()}"

    # Collision check with real production accounts
    existing_real_user = User.query.filter(
        (User.email == email) | (User.identifier == admin_id)
    ).first()
    if existing_real_user and not existing_real_user.is_demo:
        return None, 'This email or administrator ID belongs to a registered production account. Please use Normal Login Mode.'

    demo_college = get_or_create_demo_college(college_name)

    # Check existing demo account
    demo_user = User.query.filter(
        (User.email == email) | (User.identifier == admin_id)
    ).first()

    if demo_user and demo_user.is_demo:
        demo_user.set_password(password)
        demo_user.demo_session_id = secrets.token_hex(16)
        demo_user.last_login_date = datetime.utcnow()
        demo_user.is_active = True
        demo_user.registration_status = 'approved'
        db.session.commit()
        return demo_user, None

    demo_user = User(
        identifier=admin_id,
        email=email,
        role='college_admin',
        college_id=demo_college.id,
        is_active=True,
        registration_status='approved',
        is_demo=True,
        account_type='demo',
        demo_session_id=secrets.token_hex(16),
        last_login_date=datetime.utcnow()
    )
    demo_user.set_password(password)
    db.session.add(demo_user)
    db.session.flush()

    adm_profile = CollegeAdminProfile(
        user_id=demo_user.id,
        admin_id_code=admin_id,
        full_name=name,
        college_id=demo_college.id,
        registration_status='approved'
    )
    admin_ap = AdminProfile(
        user_id=demo_user.id,
        admin_id_code=admin_id,
        full_name=name,
        college_id=demo_college.id,
        registration_status='approved'
    )
    db.session.add_all([adm_profile, admin_ap])
    db.session.commit()

    return demo_user, None


def get_demo_metrics():
    """Returns inventory of active demonstration data for administrative monitoring."""
    demo_users = User.query.filter_by(is_demo=True).all()
    demo_colleges = College.query.filter_by(is_demo=True).all()
    demo_exams = Examination.query.filter_by(is_demo=True).all()

    student_count = sum(1 for u in demo_users if u.role == 'student')
    faculty_count = sum(1 for u in demo_users if u.role == 'faculty')
    admin_count = sum(1 for u in demo_users if u.role == 'college_admin')

    attempt_count = ExamAttempt.query.join(Examination).filter(Examination.is_demo == True).count()
    result_count = ExamResult.query.join(Examination).filter(Examination.is_demo == True).count()

    return {
        'total_demo_users': len(demo_users),
        'demo_students': student_count,
        'demo_faculty': faculty_count,
        'demo_admins': admin_count,
        'demo_colleges': len(demo_colleges),
        'demo_examinations': len(demo_exams),
        'demo_attempts': attempt_count,
        'demo_results': result_count,
        'users': demo_users
    }


def reset_demo_examination_data(college_id=None):
    """
    Cleans demo exam attempts and results, allowing fresh evaluation testing.
    NEVER touches any non-demo college or student data.
    """
    query = ExamAttempt.query.join(Examination).filter(Examination.is_demo == True)
    if college_id:
        query = query.filter(Examination.college_id == college_id)

    attempts = query.all()
    attempt_ids = [a.id for a in attempts]
    count = len(attempt_ids)

    if attempt_ids:
        # Delete answers and logs associated with these demo attempts
        StudentAnswer.query.filter(StudentAnswer.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)
        ExamActivityLog.query.filter(ExamActivityLog.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)
        ExamResult.query.filter(ExamResult.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)
        ExamAttempt.query.filter(ExamAttempt.id.in_(attempt_ids)).delete(synchronize_session=False)
        db.session.commit()

    return count


def purge_demo_accounts(preserve_baseline_cohort=True):
    """
    Safely removes transient demo user accounts without touching production data.
    """
    baseline_emails = {'priya.demo@demotech.edu', 'rahul.demo@demotech.edu', 'ananya.demo@demotech.edu', 'examiner@demotech.edu'}
    query = User.query.filter_by(is_demo=True)
    if preserve_baseline_cohort:
        query = query.filter(~User.email.in_(baseline_emails))

    demo_users = query.all()
    count = len(demo_users)
    for u in demo_users:
        db.session.delete(u)
    db.session.commit()
    return count

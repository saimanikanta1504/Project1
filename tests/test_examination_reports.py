import pytest
from datetime import datetime, date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, CollegeAdminProfile,
    Course, Branch, Subject, Examination, Question, Option, ExamAttempt,
    StudentAnswer, ExamResult
)
from app.utils import compute_competition_ranking


@pytest.fixture
def app_with_reports():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # College 1
        col1 = College(
            name='ABC Engineering College', code='ABCENG',
            address='Tech City, Hyderabad', email='info@abc.edu',
            contact_number='+91 40 1111', status='active'
        )
        # College 2 (for isolation testing)
        col2 = College(
            name='XYZ Tech', code='XYZTECH',
            address='Bengaluru', email='info@xyz.edu',
            contact_number='+91 80 2222', status='active'
        )
        db.session.add_all([col1, col2])
        db.session.flush()

        course1 = Course(college_id=col1.id, code='BTECH', name='Bachelor of Technology')
        db.session.add(course1)
        db.session.flush()

        branch1 = Branch(college_id=col1.id, course_id=course1.id, code='CSE', name='Computer Science')
        db.session.add(branch1)
        db.session.flush()

        sub1 = Subject(
            college_id=col1.id, course_id=course1.id, branch_id=branch1.id,
            semester=3, code='CS301', name='Data Structures', academic_year='2026-2027'
        )
        sub2_unauthorized = Subject(
            college_id=col1.id, course_id=course1.id, branch_id=branch1.id,
            semester=3, code='CS309', name='Quantum Computing', academic_year='2026-2027'
        )
        db.session.add_all([sub1, sub2_unauthorized])
        db.session.flush()

        # Faculty 1 (Authorized for Sub1 / College 1)
        fac1_u = User(identifier='FAC-ABC-01', email='fac1@abc.edu', role='faculty', college_id=col1.id)
        fac1_u.set_password('Secret123')
        fac1_p = FacultyProfile(user=fac1_u, faculty_id_code='FAC-ABC-01', first_name='Ramesh', last_name='Varma', college_id=col1.id, department_name='CSE')

        # Faculty 2 (College 2)
        fac2_u = User(identifier='FAC-XYZ-01', email='fac2@xyz.edu', role='faculty', college_id=col2.id)
        fac2_u.set_password('Secret123')
        fac2_p = FacultyProfile(user=fac2_u, faculty_id_code='FAC-XYZ-01', first_name='Suresh', last_name='Nair', college_id=col2.id, department_name='IT')

        # Faculty 3 (Other Faculty in College 1 for unauthorized exam)
        fac3_u = User(identifier='FAC-ABC-03', email='fac3@abc.edu', role='faculty', college_id=col1.id)
        fac3_u.set_password('Secret123')
        fac3_p = FacultyProfile(user=fac3_u, faculty_id_code='FAC-ABC-03', first_name='Ananya', last_name='Roy', college_id=col1.id, department_name='QC')

        # Seed 4 Eligible Students in College 1
        students = []
        for i, (fname, lname, roll) in enumerate([
            ('Student', 'A', '11765'),
            ('Student', 'B', '11766'),
            ('Student', 'C', '11767'),
            ('Student', 'D', '11768')
        ], start=1):
            u = User(identifier=roll, email=f'{roll}@abc.edu', role='student', college_id=col1.id)
            u.set_password('Secret123')
            p = StudentProfile(
                user=u, registration_number=roll, first_name=fname, last_name=lname,
                college_id=col1.id, course_id=course1.id, branch_id=branch1.id,
                semester=3, academic_year='2026-2027'
            )
            db.session.add_all([u, p])
            students.append(p)

        db.session.add_all([fac1_u, fac1_p, fac2_u, fac2_p, fac3_u, fac3_p])
        db.session.flush()

        # Closed Exam (Completed Yesterday)
        exam_closed = Examination(
            college_id=col1.id, faculty_id=fac1_p.id, course_id=course1.id,
            branch_id=branch1.id, semester=3, subject_id=sub1.id,
            title='Mid-Term Evaluation', exam_date=date.today() - timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), duration_minutes=60,
            total_marks=50.0, passing_percentage=40.0, max_attempts=1,
            negative_marking=True, negative_mark_value=0.5, status='completed'
        )
        # Unauthorized Exam (Different Faculty, Sub2)
        exam_unauthorized = Examination(
            college_id=col1.id, faculty_id=fac3_p.id, course_id=course1.id,
            branch_id=branch1.id, semester=3, subject_id=sub2_unauthorized.id,
            title='Quantum Advanced', exam_date=date.today() - timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), duration_minutes=60,
            total_marks=50.0, passing_percentage=40.0, max_attempts=1, status='completed'
        )
        # College 2 Exam (Cross-College)
        exam_col2 = Examination(
            college_id=col2.id, faculty_id=fac2_p.id, course_id=course1.id,
            branch_id=branch1.id, semester=3, subject_id=sub1.id,
            title='XYZ College Exam', exam_date=date.today(),
            start_time=time(10, 0), end_time=time(11, 0), duration_minutes=60,
            total_marks=50.0, passing_percentage=40.0, status='completed'
        )
        db.session.add_all([exam_closed, exam_unauthorized, exam_col2])
        db.session.flush()

        # Questions for exam_closed
        q1 = Question(examination_id=exam_closed.id, question_number=1, question_text='Q1 Text', marks=25.0)
        q2 = Question(examination_id=exam_closed.id, question_number=2, question_text='Q2 Text', marks=25.0)
        db.session.add_all([q1, q2])
        db.session.flush()

        opt1_c = Option(question_id=q1.id, option_number=1, option_text='Opt1', is_correct=True)
        opt1_w = Option(question_id=q1.id, option_number=2, option_text='Opt2', is_correct=False)
        opt2_c = Option(question_id=q2.id, option_number=1, option_text='Opt3', is_correct=True)
        opt2_w = Option(question_id=q2.id, option_number=2, option_text='Opt4', is_correct=False)
        db.session.add_all([opt1_c, opt1_w, opt2_c, opt2_w])
        db.session.flush()

        # Seed Attempts & Results for Competition Ranking (1224)
        # Student A (11765): 49.0 pts -> Rank 1
        att_a = ExamAttempt(examination_id=exam_closed.id, student_id=students[0].id, college_id=col1.id, status='submitted')
        db.session.add(att_a)
        db.session.flush()
        db.session.add(StudentAnswer(attempt_id=att_a.id, question_id=q1.id, selected_option_id=opt1_c.id))
        res_a = ExamResult(
            attempt_id=att_a.id, examination_id=exam_closed.id, student_id=students[0].id, college_id=col1.id,
            total_questions=2, correct_answers=2, wrong_answers=0, unanswered_questions=0,
            total_marks=50.0, obtained_marks=49.0, percentage=98.0, is_passed=True
        )

        # Student B (11766): 47.0 pts -> Rank 2 (Tied)
        att_b = ExamAttempt(examination_id=exam_closed.id, student_id=students[1].id, college_id=col1.id, status='submitted')
        db.session.add(att_b)
        db.session.flush()
        res_b = ExamResult(
            attempt_id=att_b.id, examination_id=exam_closed.id, student_id=students[1].id, college_id=col1.id,
            total_questions=2, correct_answers=1, wrong_answers=1, unanswered_questions=0,
            total_marks=50.0, obtained_marks=47.0, percentage=94.0, is_passed=True
        )

        # Student C (11767): 47.0 pts -> Rank 2 (Tied)
        att_c = ExamAttempt(examination_id=exam_closed.id, student_id=students[2].id, college_id=col1.id, status='submitted')
        db.session.add(att_c)
        db.session.flush()
        res_c = ExamResult(
            attempt_id=att_c.id, examination_id=exam_closed.id, student_id=students[2].id, college_id=col1.id,
            total_questions=2, correct_answers=1, wrong_answers=1, unanswered_questions=0,
            total_marks=50.0, obtained_marks=47.0, percentage=94.0, is_passed=True
        )

        # Student D (11768): NO ATTEMPT -> Window Closed -> Absent!
        db.session.add_all([res_a, res_b, res_c])
        db.session.commit()

        yield app

        db.drop_all()


@pytest.fixture
def client(app_with_reports):
    return app_with_reports.test_client()


def test_competition_ranking_algorithm():
    """Verify that ties receive equal rank and subsequent rank skips correctly (1, 2, 2, 4)."""
    class MockResult:
        def __init__(self, name, marks):
            self.name = name
            self.obtained_marks = marks
            self.percentage = marks

    results = [
        MockResult('Student A', 49.0),
        MockResult('Student B', 47.0),
        MockResult('Student C', 47.0),
        MockResult('Student D', 45.0)
    ]
    ranked = compute_competition_ranking(results)
    assert ranked[0].name == 'Student A' and ranked[0].competition_rank == 1
    assert ranked[1].name in ('Student B', 'Student C') and ranked[1].competition_rank == 2
    assert ranked[2].name in ('Student B', 'Student C') and ranked[2].competition_rank == 2
    assert ranked[3].name == 'Student D' and ranked[3].competition_rank == 4


def test_faculty_reports_index(client):
    """Scenario 1 & 2: Faculty can view authorized examinations and student attendance stats."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports')
    assert res.status_code == 200
    assert b'Mid-Term Evaluation' in res.data
    assert b'Data Structures' in res.data
    assert b'Examination Reports & Attendance Registry' in res.data


def test_examination_report_attendance_and_absent_detection(client):
    """Scenarios 3, 4, 6: Attended students are Present; unattempted students are Absent once window closed."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports/1')
    assert res.status_code == 200
    # Total Registered = 4 (11765, 11766, 11767, 11768)
    assert b'Total Registered' in res.data
    # Attended = 3 (Students A, B, C)
    assert b'Present' in res.data
    # Absent = 1 (Student D - 11768)
    assert b'11768' in res.data
    assert b'Absent' in res.data


def test_ranked_marks_and_ties(client):
    """Scenarios 7, 8, 9, 10: Marks retrieved from finalized results; tied scores receive same rank."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports/1')
    assert res.status_code == 200
    # Rank 1: Student A (49.0)
    assert b'#1' in res.data
    # Rank 2: Student B and C (47.0)
    assert b'#2' in res.data
    # Absent Student D does not receive marks
    assert b'Student Marks, Evaluation & Standard Competition Ranking' in res.data


def test_individual_student_performance_review(client):
    """Scenario 15: Individual student view shows correct breakdown and solutions."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports/1/student/1')
    assert res.status_code == 200
    assert b'Student A' in res.data
    assert b'11765' in res.data
    assert b'Q1 Text' in res.data
    assert b'Correct Response' in res.data


def test_security_cross_college_isolation(client):
    """Scenario 11: Faculty cannot access an examination belonging to another college."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    # Exam 3 belongs to College 2 (XYZ Tech)
    res = client.get('/faculty/examination-reports/3')
    assert res.status_code == 403


def test_security_unauthorized_subject_access(client):
    """Scenario 12: Faculty cannot access an examination created by another faculty in an unassigned subject."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    # Exam 2 is for CS309 (Quantum) under FAC-ABC-03
    res = client.get('/faculty/examination-reports/2')
    assert res.status_code == 403


def test_download_attendance_pdf(client):
    """Scenario 13: Attendance PDF generates and downloads cleanly."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports/1/download-attendance')
    assert res.status_code == 200
    assert res.mimetype == 'application/pdf'
    assert len(res.data) > 1000


def test_download_marks_pdf(client):
    """Scenario 13: Marks PDF generates and downloads cleanly."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports/1/download-marks')
    assert res.status_code == 200
    assert res.mimetype == 'application/pdf'
    assert len(res.data) > 1000


def test_download_complete_report_pdf(client):
    """Scenario 13: Complete examination report PDF generates and downloads cleanly."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports/1/download-complete-report')
    assert res.status_code == 200
    assert res.mimetype == 'application/pdf'
    assert len(res.data) > 1000


def test_export_csv_results(client):
    """Scenario 14: Results export to CSV format with correct column headers."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    res = client.get('/faculty/examination-reports/1/export-csv')
    assert res.status_code == 200
    assert res.mimetype == 'text/csv'
    csv_text = res.data.decode('utf-8')
    assert 'Rank,Roll Number,Student Name' in csv_text
    assert '11765,Student A' in csv_text
    assert '11768,Student D' in csv_text
    assert 'ABSENT,Absent' in csv_text


def test_assigned_faculty_can_view_and_download_result(client):
    """Scenario 15: Faculty assigned to subject can view student result and download PDF."""
    client.post('/auth/login', data={'identifier': 'FAC-ABC-01', 'password': 'Secret123'})
    # Result 1 belongs to Exam 1, which FAC-ABC-01 is assigned to
    res = client.get('/results/1')
    assert res.status_code == 200
    assert b'Scorecard' in res.data or b'Result' in res.data or b'11765' in res.data

    res_pdf = client.get('/results/1/download-pdf')
    assert res_pdf.status_code == 200
    assert res_pdf.mimetype == 'application/pdf'
    assert len(res_pdf.data) > 1000


import os
import uuid
from functools import wraps
from io import BytesIO
from datetime import datetime
from flask import abort, current_app, redirect, url_for, flash
from flask_login import current_user
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from app.extensions import db


def check_role(*roles):
    """Verifies that the current user is authenticated, active, approved, and belongs to one of the given roles."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    # Strict account approval check
    status = getattr(current_user, 'registration_status', 'active')
    if status in ('pending_approval', 'pending_verification') or not current_user.is_active:
        from flask_login import logout_user
        logout_user()
        flash('Your account is currently pending administrative approval. Access to portal features is restricted until approved.', 'warning')
        return redirect(url_for('auth.login'))

    if status == 'rejected':
        from flask_login import logout_user
        logout_user()
        flash('Your account registration has been rejected. Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    if status == 'deactivated':
        from flask_login import logout_user
        logout_user()
        flash('Your account has been deactivated. Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    if current_user.role not in roles:
        abort(403)
    return None


def role_required(*roles):
    """Decorator to enforce role-based access control on view functions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            res = check_role(*roles)
            if res:
                return res
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def super_admin_required(f=None):
    if f is None:
        return check_role('super_admin')
    return role_required('super_admin')(f)


def college_admin_required(f=None):
    if f is None:
        return check_role('college_admin')
    return role_required('college_admin')(f)


def faculty_required(f=None):
    if f is None:
        return check_role('faculty')
    return role_required('faculty')(f)


def student_required(f=None):
    if f is None:
        return check_role('student')
    return role_required('student')(f)


def ensure_college_access(target_college_id):
    """Enforce cross-college data isolation. Super admin has platform-wide access."""
    if not current_user.is_authenticated:
        abort(401)
    if current_user.is_super_admin:
        return True
    if current_user.college_id != target_college_id:
        abort(403)
    return True


def allowed_file(filename):
    """Verify allowed image extensions."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_college_logo(file):
    """Securely save uploaded college logo."""
    if not file or file.filename == '':
        return None
    if allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"college_{uuid.uuid4().hex[:10]}.{ext}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(upload_path)
        return unique_name
    return None


def evaluate_exam_attempt(attempt):
    """
    Evaluates an examination attempt strictly on the backend.
    Calculates correct, wrong, unanswered questions and applies negative marking if enabled.
    """
    from app.models import ExamResult, StudentAnswer, Option

    exam = attempt.examination
    answers = {a.question_id: a for a in attempt.answers}
    
    total_questions = len(exam.questions)
    correct_count = 0
    wrong_count = 0
    unanswered_count = 0
    obtained_marks = 0.0

    for q in exam.questions:
        ans = answers.get(q.id)
        if not ans or not ans.selected_option_id:
            unanswered_count += 1
            continue

        selected_opt = db.session.get(Option, ans.selected_option_id)
        if selected_opt and selected_opt.is_correct:
            correct_count += 1
            obtained_marks += q.marks
        else:
            wrong_count += 1
            if exam.negative_marking:
                deduction = q.negative_marks if q.negative_marks > 0 else exam.negative_mark_value
                obtained_marks -= deduction

    # Prevent negative overall marks
    obtained_marks = max(0.0, round(obtained_marks, 2))
    total_marks = exam.total_marks if exam.total_marks > 0 else float(total_questions)
    percentage = round((obtained_marks / total_marks) * 100, 2) if total_marks > 0 else 0.0
    is_passed = percentage >= exam.passing_percentage

    # Create or update ExamResult
    result = ExamResult.query.filter_by(attempt_id=attempt.id).first()
    if not result:
        result = ExamResult(
            attempt_id=attempt.id,
            examination_id=exam.id,
            student_id=attempt.student_id,
            college_id=attempt.college_id,
            total_questions=total_questions,
            correct_answers=correct_count,
            wrong_answers=wrong_count,
            unanswered_questions=unanswered_count,
            total_marks=total_marks,
            obtained_marks=obtained_marks,
            percentage=percentage,
            is_passed=is_passed,
            evaluated_at=datetime.utcnow()
        )
        db.session.add(result)
    else:
        result.total_questions = total_questions
        result.correct_answers = correct_count
        result.wrong_answers = wrong_count
        result.unanswered_questions = unanswered_count
        result.total_marks = total_marks
        result.obtained_marks = obtained_marks
        result.percentage = percentage
        result.is_passed = is_passed
        result.evaluated_at = datetime.utcnow()

    attempt.status = 'submitted'
    attempt.end_time = datetime.utcnow()
    db.session.commit()
    return result


def generate_result_pdf(result):
    """
    Generates an official university-style Examination Grade Sheet / Scorecard PDF.
    Uses ReportLab to return a byte buffer.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor('#163B65')
    secondary_color = colors.HexColor('#245EA8')
    text_color = colors.HexColor('#202B3C')
    success_color = colors.HexColor('#218653')
    danger_color = colors.HexColor('#D64545')
    light_bg = colors.HexColor('#F8FAFC')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=primary_color
    )

    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        textColor=secondary_color
    )

    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#64748B')
    )

    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=text_color
    )

    cell_normal = ParagraphStyle(
        'CellNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_color
    )

    elements = []

    # 1. College Header
    elements.append(Paragraph(result.college.name.upper(), title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Institution Code: {result.college.code} | {result.college.address}", meta_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("OFFICIAL ONLINE EXAMINATION SCORECARD & PERFORMANCE TRANSCRIPT", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=14))

    # 2. Student & Academic Profile Table
    student = result.student
    exam = result.examination
    
    student_data = [
        [
            Paragraph("Candidate Name:", cell_bold), Paragraph(student.full_name, cell_normal),
            Paragraph("Roll / Reg. No.:", cell_bold), Paragraph(student.registration_number, cell_bold)
        ],
        [
            Paragraph("Program / Course:", cell_bold), Paragraph(student.course.name, cell_normal),
            Paragraph("Branch / Discipline:", cell_bold), Paragraph(student.branch.name, cell_normal)
        ],
        [
            Paragraph("Semester:", cell_bold), Paragraph(f"Semester {student.semester}", cell_normal),
            Paragraph("Academic Year:", cell_bold), Paragraph(student.academic_year, cell_normal)
        ],
        [
            Paragraph("Examination Title:", cell_bold), Paragraph(exam.title, cell_normal),
            Paragraph("Subject:", cell_bold), Paragraph(f"{exam.subject.name} ({exam.subject.code})", cell_normal)
        ],
        [
            Paragraph("Exam Date:", cell_bold), Paragraph(exam.exam_date.strftime('%d-%b-%Y'), cell_normal),
            Paragraph("Attempt Number:", cell_bold), Paragraph(str(result.attempt.attempt_number), cell_normal)
        ]
    ]

    student_table = Table(student_data, colWidths=[110, 155, 110, 155])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(student_table)
    elements.append(Spacer(1, 18))

    # 3. Performance Summary Table
    perf_header = [
        Paragraph("Metric Description", cell_bold),
        Paragraph("Count / Value", cell_bold),
        Paragraph("Evaluation Weight", cell_bold)
    ]
    perf_data = [
        perf_header,
        [Paragraph("Total Examination Questions", cell_normal), Paragraph(str(result.total_questions), cell_normal), Paragraph("-", cell_normal)],
        [Paragraph("Correctly Answered", cell_normal), Paragraph(str(result.correct_answers), cell_normal), Paragraph(f"+{exam.total_marks / max(1, result.total_questions):.2f} pts each", cell_normal)],
        [Paragraph("Incorrect / Wrong Responses", cell_normal), Paragraph(str(result.wrong_answers), cell_normal), Paragraph(f"-{exam.negative_mark_value} pts (if negative marking)" if exam.negative_marking else "No deduction", cell_normal)],
        [Paragraph("Unattempted / Skipped", cell_normal), Paragraph(str(result.unanswered_questions), cell_normal), Paragraph("0 pts", cell_normal)],
        [Paragraph("Total Maximum Marks", cell_bold), Paragraph(f"{result.total_marks:.2f}", cell_bold), Paragraph("100.00%", cell_normal)],
        [Paragraph("Marks Obtained", cell_bold), Paragraph(f"{result.obtained_marks:.2f}", cell_bold), Paragraph(f"{result.percentage:.2f}%", cell_bold)],
    ]

    perf_table = Table(perf_data, colWidths=[240, 140, 150])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
    ]))
    elements.append(perf_table)
    elements.append(Spacer(1, 20))

    # 4. Result Outcome Box
    status_text = "PASS" if result.is_passed else "FAIL"
    status_bg = colors.HexColor('#DCFCE7') if result.is_passed else colors.HexColor('#FEE2E2')
    status_border = success_color if result.is_passed else danger_color

    outcome_data = [
        [
            Paragraph("FINAL RESULT STATUS:", cell_bold),
            Paragraph(f"<b><font color='{status_border.hexval()}'>{status_text}</font></b> (Qualifying Mark: {exam.passing_percentage}%)", cell_bold)
        ],
        [
            Paragraph("Evaluation Timestamp:", cell_bold),
            Paragraph(result.evaluated_at.strftime('%d-%b-%Y %H:%M:%S UTC'), cell_normal)
        ]
    ]
    outcome_table = Table(outcome_data, colWidths=[180, 350])
    outcome_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), status_bg),
        ('BOX', (0, 0), (-1, -1), 1, status_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(outcome_table)
    elements.append(Spacer(1, 35))

    # 5. Signatures and Verification
    sig_data = [
        [
            Paragraph("<b>Automated Evaluation Engine</b><br/>Centralized Examination Portal", meta_style),
            Paragraph("<b>Controller of Examinations</b><br/>" + result.college.name, meta_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 15))

    footer_text = Paragraph(
        "<i>Note: This is an authentic computer-generated score sheet generated by the Multi-College Examination Platform. No physical signature is required.</i>",
        meta_style
    )
    elements.append(footer_text)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def compute_competition_ranking(results):
    """
    Computes Standard Competition Ranking (1224) based on obtained marks descending.
    Ties receive the same rank; subsequent ranks skip according to the number of tied students.
    """
    sorted_results = sorted(results, key=lambda r: (r.obtained_marks, r.percentage), reverse=True)
    ranked = []
    current_rank = 1
    for i, res in enumerate(sorted_results):
        if i > 0 and res.obtained_marks < sorted_results[i - 1].obtained_marks:
            current_rank = i + 1
        res.competition_rank = current_rank
        ranked.append(res)
    return ranked


def generate_attendance_pdf(exam, attendance_records, summary_stats):
    """
    Generates an official institutional Examination Attendance Report PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor('#163B65')
    secondary_color = colors.HexColor('#245EA8')
    text_color = colors.HexColor('#202B3C')
    success_color = colors.HexColor('#218653')
    danger_color = colors.HexColor('#D64545')
    light_bg = colors.HexColor('#F8FAFC')

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=18, leading=22, alignment=TA_CENTER, textColor=primary_color
    )
    subtitle_style = ParagraphStyle(
        'DocSub', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=12, leading=16, alignment=TA_CENTER, textColor=secondary_color
    )
    meta_style = ParagraphStyle(
        'MetaStyle', parent=styles['Normal'], fontName='Helvetica',
        fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor('#64748B')
    )
    cell_bold = ParagraphStyle(
        'CellBold', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=9, leading=12, textColor=text_color
    )
    cell_normal = ParagraphStyle(
        'CellNormal', parent=styles['Normal'], fontName='Helvetica',
        fontSize=9, leading=12, textColor=text_color
    )

    elements = []

    # 1. Header
    elements.append(Paragraph(exam.college.name.upper(), title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Institution Code: {exam.college.code} | {exam.college.address}", meta_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("OFFICIAL EXAMINATION ATTENDANCE RECORD & SESSION AUDIT", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=14))

    # 2. Exam Metadata Table
    exam_info = [
        [
            Paragraph("Examination:", cell_bold), Paragraph(exam.title, cell_normal),
            Paragraph("Subject:", cell_bold), Paragraph(f"{exam.subject.name} ({exam.subject.code})", cell_normal)
        ],
        [
            Paragraph("Program / Branch:", cell_bold), Paragraph(f"{exam.course.name} - {exam.branch.name}", cell_normal),
            Paragraph("Semester:", cell_bold), Paragraph(f"Semester {exam.semester}", cell_normal)
        ],
        [
            Paragraph("Examination Date:", cell_bold), Paragraph(exam.exam_date.strftime('%d-%b-%Y'), cell_normal),
            Paragraph("Time Window:", cell_bold), Paragraph(f"{exam.start_time.strftime('%H:%M')} - {exam.end_time.strftime('%H:%M')}", cell_normal)
        ]
    ]
    t_info = Table(exam_info, colWidths=[110, 155, 110, 155])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 14))

    # 3. Attendance Statistics Summary Bar
    stat_data = [
        [
            Paragraph(f"<b>Registered:</b> {summary_stats['total_registered']}", cell_normal),
            Paragraph(f"<b>Present:</b> {summary_stats['present_count']}", cell_normal),
            Paragraph(f"<b>Absent:</b> {summary_stats['absent_count']}", cell_normal),
            Paragraph(f"<b>In Progress:</b> {summary_stats['in_progress_count']}", cell_normal),
            Paragraph(f"<b>Attendance Rate:</b> {summary_stats['attendance_percentage']}%", cell_bold)
        ]
    ]
    t_stat = Table(stat_data, colWidths=[105, 105, 105, 105, 110])
    t_stat.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(t_stat)
    elements.append(Spacer(1, 14))

    # 4. Student Attendance Ledger
    table_header = [
        Paragraph("S.No", cell_bold),
        Paragraph("Roll Number", cell_bold),
        Paragraph("Student Name", cell_bold),
        Paragraph("Branch", cell_bold),
        Paragraph("Attendance Status", cell_bold),
        Paragraph("Timestamp / Session", cell_bold)
    ]
    table_rows = [table_header]

    for item in attendance_records:
        st = item['student']
        att = item.get('attempt')
        status_str = item['status']
        status_color = '#218653' if status_str == 'Present' else ('#D64545' if status_str == 'Absent' else '#D99A25')
        
        time_str = att.start_time.strftime('%H:%M:%S') if att and att.start_time else '-'
        if att and att.end_time:
            time_str += f" to {att.end_time.strftime('%H:%M:%S')}"

        table_rows.append([
            Paragraph(str(item['s_no']), cell_normal),
            Paragraph(st.registration_number, cell_bold),
            Paragraph(st.full_name, cell_normal),
            Paragraph(st.branch.code, cell_normal),
            Paragraph(f"<font color='{status_color}'><b>{status_str.upper()}</b></font>", cell_bold),
            Paragraph(time_str, cell_normal)
        ])

    ledger_table = Table(table_rows, colWidths=[40, 95, 145, 60, 95, 95])
    ledger_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg])
    ]))
    elements.append(ledger_table)
    elements.append(Spacer(1, 25))

    # 5. Signatures
    sig_data = [
        [
            Paragraph("<b>Faculty In-Charge / Invigilator</b><br/>" + exam.faculty.full_name, meta_style),
            Paragraph("<b>Head of Department / COE</b><br/>" + exam.college.name, meta_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_marks_pdf(exam, ranked_results, summary_stats):
    """
    Generates an official institutional Ranked Examination Marks & Merit Sheet PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor('#163B65')
    secondary_color = colors.HexColor('#245EA8')
    text_color = colors.HexColor('#202B3C')
    success_color = colors.HexColor('#218653')
    danger_color = colors.HexColor('#D64545')
    light_bg = colors.HexColor('#F8FAFC')

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=18, leading=22, alignment=TA_CENTER, textColor=primary_color
    )
    subtitle_style = ParagraphStyle(
        'DocSub', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=12, leading=16, alignment=TA_CENTER, textColor=secondary_color
    )
    meta_style = ParagraphStyle(
        'MetaStyle', parent=styles['Normal'], fontName='Helvetica',
        fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor('#64748B')
    )
    cell_bold = ParagraphStyle(
        'CellBold', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=9, leading=12, textColor=text_color
    )
    cell_normal = ParagraphStyle(
        'CellNormal', parent=styles['Normal'], fontName='Helvetica',
        fontSize=9, leading=12, textColor=text_color
    )

    elements = []

    # 1. Header
    elements.append(Paragraph(exam.college.name.upper(), title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Institution Code: {exam.college.code} | {exam.college.address}", meta_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("OFFICIAL STUDENT MARKS, MERIT LIST & RANKING LEDGER", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=14))

    # 2. Exam Metadata Table
    exam_info = [
        [
            Paragraph("Examination:", cell_bold), Paragraph(exam.title, cell_normal),
            Paragraph("Subject:", cell_bold), Paragraph(f"{exam.subject.name} ({exam.subject.code})", cell_normal)
        ],
        [
            Paragraph("Program / Branch:", cell_bold), Paragraph(f"{exam.course.name} - {exam.branch.name}", cell_normal),
            Paragraph("Semester:", cell_bold), Paragraph(f"Semester {exam.semester}", cell_normal)
        ],
        [
            Paragraph("Total Marks:", cell_bold), Paragraph(f"{exam.total_marks:.2f} Pts", cell_normal),
            Paragraph("Passing Mark:", cell_bold), Paragraph(f"{exam.passing_percentage}%", cell_normal)
        ]
    ]
    t_info = Table(exam_info, colWidths=[110, 155, 110, 155])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 14))

    # 3. Marks Statistics Summary Bar
    stat_data = [
        [
            Paragraph(f"<b>Evaluated:</b> {summary_stats['total_evaluated']}", cell_normal),
            Paragraph(f"<b>Highest:</b> {summary_stats['highest_marks']}", cell_normal),
            Paragraph(f"<b>Lowest:</b> {summary_stats['lowest_marks']}", cell_normal),
            Paragraph(f"<b>Average:</b> {summary_stats['average_marks']}", cell_normal),
            Paragraph(f"<b>Pass Rate:</b> {summary_stats['pass_percentage']}%", cell_bold)
        ]
    ]
    t_stat = Table(stat_data, colWidths=[105, 105, 105, 105, 110])
    t_stat.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(t_stat)
    elements.append(Spacer(1, 14))

    # 4. Student Marks & Ranking Table
    table_header = [
        Paragraph("Rank", cell_bold),
        Paragraph("Roll Number", cell_bold),
        Paragraph("Student Name", cell_bold),
        Paragraph("Marks", cell_bold),
        Paragraph("Max", cell_bold),
        Paragraph("Percentage", cell_bold),
        Paragraph("Correct/Wrong", cell_bold),
        Paragraph("Result", cell_bold)
    ]
    table_rows = [table_header]

    for res in ranked_results:
        st = res.student
        status_color = '#218653' if res.is_passed else '#D64545'
        status_label = 'PASS' if res.is_passed else 'FAIL'

        table_rows.append([
            Paragraph(f"<b>#{res.competition_rank}</b>", cell_bold),
            Paragraph(st.registration_number, cell_bold),
            Paragraph(st.full_name, cell_normal),
            Paragraph(f"<b>{res.obtained_marks:.2f}</b>", cell_bold),
            Paragraph(f"{res.total_marks:.2f}", cell_normal),
            Paragraph(f"{res.percentage:.2f}%", cell_bold),
            Paragraph(f"{res.correct_answers}C / {res.wrong_answers}W", cell_normal),
            Paragraph(f"<font color='{status_color}'><b>{status_label}</b></font>", cell_bold)
        ])

    marks_table = Table(table_rows, colWidths=[40, 85, 130, 50, 45, 60, 65, 55])
    marks_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg])
    ]))
    elements.append(marks_table)
    elements.append(Spacer(1, 25))

    # 5. Signatures
    sig_data = [
        [
            Paragraph("<b>Faculty Evaluator</b><br/>" + exam.faculty.full_name, meta_style),
            Paragraph("<b>Controller of Examinations</b><br/>" + exam.college.name, meta_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_complete_exam_report_pdf(exam, ranked_results, attendance_records, summary_stats):
    """
    Generates a Comprehensive Multi-Section Examination Report PDF containing
    Executive Summary, Attendance Ledger, and Ranked Merit List.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor('#163B65')
    secondary_color = colors.HexColor('#245EA8')
    text_color = colors.HexColor('#202B3C')
    light_bg = colors.HexColor('#F8FAFC')

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=18, leading=22, alignment=TA_CENTER, textColor=primary_color
    )
    subtitle_style = ParagraphStyle(
        'DocSub', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=12, leading=16, alignment=TA_CENTER, textColor=secondary_color
    )
    section_style = ParagraphStyle(
        'SecStyle', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=11, leading=14, textColor=primary_color
    )
    meta_style = ParagraphStyle(
        'MetaStyle', parent=styles['Normal'], fontName='Helvetica',
        fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor('#64748B')
    )
    cell_bold = ParagraphStyle(
        'CellBold', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=8.5, leading=11, textColor=text_color
    )
    cell_normal = ParagraphStyle(
        'CellNormal', parent=styles['Normal'], fontName='Helvetica',
        fontSize=8.5, leading=11, textColor=text_color
    )

    elements = []

    # 1. Header
    elements.append(Paragraph(exam.college.name.upper(), title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Institution Code: {exam.college.code} | {exam.college.address}", meta_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("COMPREHENSIVE EXAMINATION PERFORMANCE & AUDIT REPORT", subtitle_style))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=12))

    # 2. Executive Overview Table
    overview_data = [
        [
            Paragraph("Examination Title:", cell_bold), Paragraph(exam.title, cell_normal),
            Paragraph("Subject:", cell_bold), Paragraph(f"{exam.subject.name} ({exam.subject.code})", cell_normal)
        ],
        [
            Paragraph("Program / Branch:", cell_bold), Paragraph(f"{exam.course.name} - {exam.branch.name}", cell_normal),
            Paragraph("Semester:", cell_bold), Paragraph(f"Semester {exam.semester}", cell_normal)
        ],
        [
            Paragraph("Exam Date & Duration:", cell_bold), Paragraph(f"{exam.exam_date.strftime('%d-%b-%Y')} ({exam.duration_minutes} Mins)", cell_normal),
            Paragraph("Total Marks / Pass %:", cell_bold), Paragraph(f"{exam.total_marks:.2f} Pts / {exam.passing_percentage}%", cell_normal)
        ],
        [
            Paragraph("Total Registered:", cell_bold), Paragraph(str(summary_stats['total_registered']), cell_normal),
            Paragraph("Attendance Rate:", cell_bold), Paragraph(f"{summary_stats['attendance_percentage']}% ({summary_stats['present_count']} Present / {summary_stats['absent_count']} Absent)", cell_normal)
        ],
        [
            Paragraph("Average Score:", cell_bold), Paragraph(f"{summary_stats['average_marks']:.2f} Pts", cell_normal),
            Paragraph("Highest / Lowest:", cell_bold), Paragraph(f"{summary_stats['highest_marks']:.2f} / {summary_stats['lowest_marks']:.2f} Pts", cell_normal)
        ],
        [
            Paragraph("Pass Percentage:", cell_bold), Paragraph(f"{summary_stats['pass_percentage']}%", cell_bold),
            Paragraph("Faculty In-Charge:", cell_bold), Paragraph(exam.faculty.full_name, cell_normal)
        ]
    ]
    t_over = Table(overview_data, colWidths=[120, 150, 120, 150])
    t_over.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_over)
    elements.append(Spacer(1, 14))

    # 3. Section: Ranked Student Marks
    elements.append(Paragraph("1. Ranked Student Marks & Merit Ledger", section_style))
    elements.append(Spacer(1, 6))

    marks_rows = [[
        Paragraph("Rank", cell_bold), Paragraph("Roll No", cell_bold),
        Paragraph("Candidate Name", cell_bold), Paragraph("Marks", cell_bold),
        Paragraph("Max", cell_bold), Paragraph("Percentage", cell_bold),
        Paragraph("Correct", cell_bold), Paragraph("Wrong", cell_bold),
        Paragraph("Status", cell_bold)
    ]]

    for res in ranked_results:
        st = res.student
        color = '#218653' if res.is_passed else '#D64545'
        label = 'PASS' if res.is_passed else 'FAIL'
        marks_rows.append([
            Paragraph(f"<b>#{res.competition_rank}</b>", cell_bold),
            Paragraph(st.registration_number, cell_bold),
            Paragraph(st.full_name, cell_normal),
            Paragraph(f"{res.obtained_marks:.2f}", cell_bold),
            Paragraph(f"{res.total_marks:.2f}", cell_normal),
            Paragraph(f"{res.percentage:.2f}%", cell_bold),
            Paragraph(str(res.correct_answers), cell_normal),
            Paragraph(str(res.wrong_answers), cell_normal),
            Paragraph(f"<font color='{color}'><b>{label}</b></font>", cell_bold)
        ])

    t_marks = Table(marks_rows, colWidths=[40, 85, 140, 45, 40, 60, 45, 45, 40])
    t_marks.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg])
    ]))
    elements.append(t_marks)
    elements.append(Spacer(1, 14))

    # 4. Section: Attendance Status Summary
    elements.append(Paragraph("2. Candidate Attendance Audit", section_style))
    elements.append(Spacer(1, 6))

    att_rows = [[
        Paragraph("S.No", cell_bold), Paragraph("Roll No", cell_bold),
        Paragraph("Candidate Name", cell_bold), Paragraph("Branch", cell_bold),
        Paragraph("Status", cell_bold), Paragraph("Session Log", cell_bold)
    ]]

    for item in attendance_records:
        st = item['student']
        att = item.get('attempt')
        status_str = item['status']
        status_color = '#218653' if status_str == 'Present' else ('#D64545' if status_str == 'Absent' else '#D99A25')
        time_str = att.start_time.strftime('%H:%M:%S') if att and att.start_time else '-'
        if att and att.end_time:
            time_str += f" - {att.end_time.strftime('%H:%M:%S')}"

        att_rows.append([
            Paragraph(str(item['s_no']), cell_normal),
            Paragraph(st.registration_number, cell_bold),
            Paragraph(st.full_name, cell_normal),
            Paragraph(st.branch.code, cell_normal),
            Paragraph(f"<font color='{status_color}'><b>{status_str}</b></font>", cell_bold),
            Paragraph(time_str, cell_normal)
        ])

    t_att = Table(att_rows, colWidths=[35, 95, 160, 60, 80, 110])
    t_att.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg])
    ]))
    elements.append(t_att)
    elements.append(Spacer(1, 20))

    # 5. Signatures
    sig_data = [
        [
            Paragraph("<b>Faculty In-Charge</b><br/>" + exam.faculty.full_name, meta_style),
            Paragraph("<b>Controller of Examinations</b><br/>" + exam.college.name, meta_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


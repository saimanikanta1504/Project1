import os
from datetime import datetime, date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    College, User, StudentProfile, FacultyProfile, CollegeAdminProfile, AdminProfile,
    Course, Branch, Subject, Examination, Question, Option, ExamAttempt,
    StudentAnswer, ExamResult, FacultySubjectAssignment
)

app = create_app('development')

def seed():
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding Super Administrator...")
        super_admin_user = User(
            identifier='SUPERADMIN',
            email='superadmin@university.edu',
            role='super_admin',
            college_id=None,
            is_active=True,
            registration_status='approved'
        )
        super_admin_user.set_password('Password@123')
        db.session.add(super_admin_user)

        # ---------------------------------------------------------
        # College 1: ABC Engineering College
        # ---------------------------------------------------------
        print("Seeding College 1: ABC Engineering College...")
        col1 = College(
            name='ABC Engineering College',
            code='ABCENG',
            address='Survey No. 45, Tech City Road, Gachibowli, Hyderabad, Telangana',
            email='info@abccollege.edu',
            contact_number='+91 40 2311 8899',
            logo_filename='default_college_logo.png',
            email_domain='abccollege.edu',
            status='active'
        )
        db.session.add(col1)
        db.session.flush()

        # College 1 Admin
        adm1_user = User(
            identifier='ADM-ABC-01',
            email='admin@abccollege.edu',
            role='college_admin',
            college_id=col1.id,
            is_active=True
        )
        adm1_user.set_password('Password@123')
        db.session.add(adm1_user)
        db.session.flush()

        adm1_profile = CollegeAdminProfile(
            user_id=adm1_user.id,
            admin_id_code='ADM-ABC-01',
            full_name='Dr. R. Ramanathan',
            college_id=col1.id,
            contact_number='+91 40 2311 8890'
        )
        adm1_ap = AdminProfile(
            user_id=adm1_user.id,
            admin_id_code='ADM-ABC-01',
            full_name='Dr. R. Ramanathan',
            college_id=col1.id,
            contact_number='+91 40 2311 8890',
            registration_status='approved'
        )
        db.session.add_all([adm1_profile, adm1_ap])

        # College 1 Courses
        c_btech = Course(college_id=col1.id, code='BTECH', name='Bachelor of Technology', duration_years=4)
        c_mca = Course(college_id=col1.id, code='MCA', name='Master of Computer Applications', duration_years=2)
        db.session.add_all([c_btech, c_mca])
        db.session.flush()

        # College 1 Branches
        b_cse = Branch(college_id=col1.id, course_id=c_btech.id, code='CSE', name='Computer Science & Engineering')
        b_ece = Branch(college_id=col1.id, course_id=c_btech.id, code='ECE', name='Electronics & Communication Engineering')
        db.session.add_all([b_cse, b_ece])
        db.session.flush()

        # College 1 Subjects (Semester 3 CSE)
        sub_ds = Subject(college_id=col1.id, course_id=c_btech.id, branch_id=b_cse.id, semester=3, code='CS301', name='Data Structures and Algorithms', academic_year='2026-2027')
        sub_dbms = Subject(college_id=col1.id, course_id=c_btech.id, branch_id=b_cse.id, semester=3, code='CS302', name='Database Management Systems', academic_year='2026-2027')
        sub_java = Subject(college_id=col1.id, course_id=c_btech.id, branch_id=b_cse.id, semester=3, code='CS303', name='Java Object-Oriented Programming', academic_year='2026-2027')
        sub_math = Subject(college_id=col1.id, course_id=c_btech.id, branch_id=b_cse.id, semester=3, code='CS304', name='Discrete Mathematical Structures', academic_year='2026-2027')
        db.session.add_all([sub_ds, sub_dbms, sub_java, sub_math])
        db.session.flush()

        # College 1 Faculty
        fac1_user = User(
            identifier='FAC-ABC-01',
            email='anita.sharma@abccollege.edu',
            role='faculty',
            college_id=col1.id,
            is_active=True
        )
        fac1_user.set_password('Password@123')
        db.session.add(fac1_user)
        db.session.flush()

        fac1_profile = FacultyProfile(
            user_id=fac1_user.id,
            faculty_id_code='FAC-ABC-01',
            first_name='Anita',
            last_name='Sharma',
            college_id=col1.id,
            designation='Associate Professor',
            department_name='Computer Science & Engineering',
            contact_number='+91 98490 12345'
        )
        db.session.add(fac1_profile)
        db.session.flush()

        # Assign Faculty to Subjects
        fsa1 = FacultySubjectAssignment(college_id=col1.id, faculty_id=fac1_profile.id, subject_id=sub_ds.id)
        fsa2 = FacultySubjectAssignment(college_id=col1.id, faculty_id=fac1_profile.id, subject_id=sub_dbms.id)
        fsa3 = FacultySubjectAssignment(college_id=col1.id, faculty_id=fac1_profile.id, subject_id=sub_java.id)
        fsa4 = FacultySubjectAssignment(college_id=col1.id, faculty_id=fac1_profile.id, subject_id=sub_math.id)
        db.session.add_all([fsa1, fsa2, fsa3, fsa4])

        # College 1 Students
        # Student 1: Sai Kumar (Active candidate)
        st1_user = User(
            identifier='2025DAMBT11765',
            email='sai.kumar@abccollege.edu',
            role='student',
            college_id=col1.id,
            is_active=True
        )
        st1_user.set_password('Password@123')
        db.session.add(st1_user)
        db.session.flush()

        st1_profile = StudentProfile(
            user_id=st1_user.id,
            registration_number='2025DAMBT11765',
            first_name='Sai',
            last_name='Kumar',
            college_id=col1.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            academic_year='2026-2027',
            contact_number='+91 91234 56789'
        )
        db.session.add(st1_profile)

        # Student 2: Pooja Reddy (Completed exam record for immediate result/PDF inspection)
        st2_user = User(
            identifier='2025DAMBT11766',
            email='pooja.reddy@abccollege.edu',
            role='student',
            college_id=col1.id,
            is_active=True
        )
        st2_user.set_password('Password@123')
        db.session.add(st2_user)
        db.session.flush()

        st2_profile = StudentProfile(
            user_id=st2_user.id,
            registration_number='2025DAMBT11766',
            first_name='Pooja',
            last_name='Reddy',
            college_id=col1.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            academic_year='2026-2027',
            contact_number='+91 98765 43210'
        )
        db.session.add(st2_profile)

        # Student 3: Rahul Sharma
        st3_user = User(
            identifier='2025DAMBT11767',
            email='rahul.sharma@abccollege.edu',
            role='student',
            college_id=col1.id,
            is_active=True
        )
        st3_user.set_password('Password@123')
        db.session.add(st3_user)
        db.session.flush()

        st3_profile = StudentProfile(
            user_id=st3_user.id,
            registration_number='2025DAMBT11767',
            first_name='Rahul',
            last_name='Sharma',
            college_id=col1.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            academic_year='2026-2027',
            contact_number='+91 98765 11111'
        )
        db.session.add(st3_profile)

        # Student 4: Sneha Patel
        st4_user = User(
            identifier='2025DAMBT11768',
            email='sneha.patel@abccollege.edu',
            role='student',
            college_id=col1.id,
            is_active=True
        )
        st4_user.set_password('Password@123')
        db.session.add(st4_user)
        db.session.flush()

        st4_profile = StudentProfile(
            user_id=st4_user.id,
            registration_number='2025DAMBT11768',
            first_name='Sneha',
            last_name='Patel',
            college_id=col1.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            academic_year='2026-2027',
            contact_number='+91 98765 22222'
        )
        db.session.add(st4_profile)

        # Student 5: Vikram Rao
        st5_user = User(
            identifier='2025DAMBT11769',
            email='vikram.rao@abccollege.edu',
            role='student',
            college_id=col1.id,
            is_active=True
        )
        st5_user.set_password('Password@123')
        db.session.add(st5_user)
        db.session.flush()

        st5_profile = StudentProfile(
            user_id=st5_user.id,
            registration_number='2025DAMBT11769',
            first_name='Vikram',
            last_name='Rao',
            college_id=col1.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            academic_year='2026-2027',
            contact_number='+91 98765 33333'
        )
        db.session.add(st5_profile)
        db.session.flush()

        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # ------------------------------------------------------------------
        # Examination 0 (YESTERDAY - COMPLETED): DBMS Assessment
        # Used for realistic Attendance (Present & Absent) & Tied Rankings
        # ------------------------------------------------------------------
        exam0 = Examination(
            college_id=col1.id,
            faculty_id=fac1_profile.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            subject_id=sub_dbms.id,
            title='Database Systems Performance & Relational Design Assessment',
            instructions='Comprehensive evaluation on Relational Algebra, Normalization & SQL Queries.',
            exam_date=yesterday,
            start_time=time(10, 0),
            end_time=time(11, 30),
            duration_minutes=60,
            total_marks=50.0,
            passing_percentage=40.0,
            max_attempts=1,
            negative_marking=True,
            negative_mark_value=0.5,
            status='completed'
        )
        db.session.add(exam0)
        db.session.flush()

        q0_1 = Question(
            examination_id=exam0.id,
            question_number=1,
            question_text='In Relational Database Design, which Normal Form eliminates Transitive Functional Dependencies?',
            marks=25.0,
            negative_marks=0.5,
            explanation='Third Normal Form (3NF) requires 2NF and mandates that no non-prime attribute is transitively dependent on the primary key.'
        )
        q0_2 = Question(
            examination_id=exam0.id,
            question_number=2,
            question_text='Which ACID property ensures that all operations within a transaction are completed successfully, or none are?',
            marks=25.0,
            negative_marks=0.5,
            explanation='Atomicity requires that each transaction be all-or-nothing: if one part fails, the entire transaction fails.'
        )
        db.session.add_all([q0_1, q0_2])
        db.session.flush()

        db.session.add_all([
            Option(question_id=q0_1.id, option_number=1, option_text='First Normal Form (1NF)', is_correct=False),
            Option(question_id=q0_1.id, option_number=2, option_text='Second Normal Form (2NF)', is_correct=False),
            Option(question_id=q0_1.id, option_number=3, option_text='Third Normal Form (3NF)', is_correct=True),
            Option(question_id=q0_1.id, option_number=4, option_text='BCNF', is_correct=False),
            Option(question_id=q0_2.id, option_number=1, option_text='Atomicity', is_correct=True),
            Option(question_id=q0_2.id, option_number=2, option_text='Consistency', is_correct=False),
            Option(question_id=q0_2.id, option_number=3, option_text='Isolation', is_correct=False),
            Option(question_id=q0_2.id, option_number=4, option_text='Durability', is_correct=False),
        ])
        exam0.calculate_total_marks()
        db.session.flush()

        # ------------------------------------------------------------------
        # Examination 1 (TODAY): Data Structures & Algorithms Mid-Term
        # ------------------------------------------------------------------
        exam1 = Examination(
            college_id=col1.id,
            faculty_id=fac1_profile.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            subject_id=sub_ds.id,
            title='Mid-Term Examination: Data Structures & Algorithms',
            instructions='1. Read each question carefully.\n2. Negative marking: -0.25 points for incorrect answers.\n3. Server timer synchronizes automatically.\n4. Avoid tab switching to prevent integrity flags.',
            exam_date=today,
            start_time=time(9, 0),
            end_time=time(23, 59),
            duration_minutes=45,
            passing_percentage=40.0,
            max_attempts=1,
            negative_marking=True,
            negative_mark_value=0.25,
            status='active'
        )
        db.session.add(exam1)
        db.session.flush()

        ds_questions = [
            {
                'text': 'Which of the following data structures operates strictly on a Last-In, First-Out (LIFO) access principle?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'A Stack operates strictly on the LIFO principle where the element inserted last is removed first.',
                'options': [('Queue', False), ('Stack', True), ('Binary Search Tree', False), ('Array List', False)]
            },
            {
                'text': 'What is the worst-case time complexity of searching for an element in an unsorted array of size N?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'In an unsorted array, linear search must inspect every element up to the N-th position in the worst case, yielding O(N).',
                'options': [('O(1)', False), ('O(log N)', False), ('O(N)', True), ('O(N^2)', False)]
            },
            {
                'text': 'Which tree traversal visits nodes in strictly ascending numerical order in a Binary Search Tree (BST)?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'In-order traversal visits the Left subtree, current Root, and Right subtree, yielding values in sorted order for a standard BST.',
                'options': [('Pre-order', False), ('In-order', True), ('Post-order', False), ('Level-order', False)]
            },
            {
                'text': 'In a circular queue implemented using an array of capacity N, what condition verifies the queue is completely full?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'A circular queue avoids boundary drift by checking (rear + 1) % N == front.',
                'options': [('rear == front', False), ('(rear + 1) % N == front', True), ('rear == N - 1', False), ('front == rear + 1', False)]
            },
            {
                'text': 'What is the worst-case auxiliary space complexity of recursive Depth First Search (DFS) on a graph with V vertices?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'In a degenerate or linear graph, the recursive call stack can hold all V vertices simultaneously, requiring O(V) memory.',
                'options': [('O(1)', False), ('O(V)', True), ('O(V^2)', False), ('O(E)', False)]
            },
            {
                'text': 'Which asymptotic notation defines both an upper and lower bound (asymptotically tight bound) on algorithmic running time?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'Big Theta (Θ) notation provides an asymptotically tight bound sandwiched between constants c1*g(n) and c2*g(n).',
                'options': [('Big O (O)', False), ('Big Omega (Ω)', False), ('Big Theta (Θ)', True), ('Little o (o)', False)]
            },
            {
                'text': 'What is the height balance condition enforced for every node in an AVL self-balancing binary search tree?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'An AVL tree requires |Height(LeftSubtree) - Height(RightSubtree)| <= 1 for every node.',
                'options': [('|Height(Left) - Height(Right)| <= 1', True), ('Height(Left) == Height(Right)', False), ('Height <= log2(N)', False), ('Balance factor == 0 only', False)]
            },
            {
                'text': 'Which collision resolution strategy creates a linked list of records for each index in a hash table?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'Separate Chaining resolves collisions by appending colliding keys into a linked list at the hashed bucket index.',
                'options': [('Linear Probing', False), ('Quadratic Probing', False), ('Separate Chaining', True), ('Double Hashing', False)]
            },
            {
                'text': 'What is the minimum number of queues required to implement a functional Stack data structure?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'Two queues are traditionally required to implement a Stack (one for storage and one for element reversal/push manipulation).',
                'options': [('1', False), ('2', True), ('3', False), ('4', False)]
            },
            {
                'text': 'Which sorting algorithm has a guaranteed worst-case time complexity of O(N log N) while executing in-place?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'Heap Sort runs in O(N log N) worst-case time and sorts strictly in-place with O(1) auxiliary space.',
                'options': [('Quick Sort', False), ('Heap Sort', True), ('Merge Sort', False), ('Bubble Sort', False)]
            }
        ]

        created_ds_questions = []
        for idx, qdata in enumerate(ds_questions, start=1):
            q = Question(
                examination_id=exam1.id,
                question_number=idx,
                question_text=qdata['text'],
                marks=qdata['marks'],
                negative_marks=qdata['neg'],
                explanation=qdata['exp']
            )
            db.session.add(q)
            db.session.flush()
            created_ds_questions.append(q)

            for opt_idx, (otext, is_cor) in enumerate(qdata['options'], start=1):
                opt = Option(question_id=q.id, option_number=opt_idx, option_text=otext, is_correct=is_cor)
                db.session.add(opt)

        exam1.calculate_total_marks()

        # ------------------------------------------------------------------
        # Examination 2 (TODAY): Database Management Systems Unit Test
        # ------------------------------------------------------------------
        exam2 = Examination(
            college_id=col1.id,
            faculty_id=fac1_profile.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            subject_id=sub_dbms.id,
            title='Unit Assessment 1: Relational Database Management Systems',
            instructions='1. Covers Relational Algebra, Normalization, and ACID properties.\n2. Negative marking: 0.25 points deduction for incorrect answers.\n3. Complete within 30 minutes.',
            exam_date=today,
            start_time=time(10, 0),
            end_time=time(23, 59),
            duration_minutes=30,
            passing_percentage=40.0,
            max_attempts=1,
            negative_marking=True,
            negative_mark_value=0.25,
            status='active'
        )
        db.session.add(exam2)
        db.session.flush()

        dbms_questions = [
            {
                'text': 'Which component of ACID transaction properties ensures that all operations in a transaction succeed, or none do?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'Atomicity ensures that all transaction modifications occur as a single atomic unit, or all are completely aborted.',
                'options': [('Atomicity', True), ('Consistency', False), ('Isolation', False), ('Durability', False)]
            },
            {
                'text': 'In relational database normalization, a table is in Second Normal Form (2NF) if it is in 1NF and contains no:',
                'marks': 1.0, 'neg': 0.25,
                'exp': '2NF eliminates partial functional dependencies on candidate keys.',
                'options': [('Transitive dependency', False), ('Partial dependency', True), ('Multi-valued dependency', False), ('Join dependency', False)]
            },
            {
                'text': 'Which SQL command is classified under Data Definition Language (DDL)?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'ALTER TABLE is a DDL statement used to modify schema definitions.',
                'options': [('SELECT', False), ('UPDATE', False), ('ALTER TABLE', True), ('INSERT', False)]
            },
            {
                'text': 'What type of lock allows concurrent transactions to read a data item but prevents any transaction from writing to it?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'Shared Lock (S-lock) permits concurrent read access while blocking exclusive writes.',
                'options': [('Exclusive Lock (X)', False), ('Shared Lock (S)', True), ('Two-Phase Lock', False), ('Deadlock', False)]
            },
            {
                'text': 'Which relational algebra operator performs horizontal selection of rows satisfying a given condition?',
                'marks': 1.0, 'neg': 0.25,
                'exp': 'Sigma (σ) represents the Select operator which filters tuples (rows) matching a predicate.',
                'options': [('Pi (π)', False), ('Sigma (σ)', True), ('Rho (ρ)', False), ('Cartesian Product (×)', False)]
            }
        ]

        for idx, qdata in enumerate(dbms_questions, start=1):
            q = Question(
                examination_id=exam2.id,
                question_number=idx,
                question_text=qdata['text'],
                marks=qdata['marks'],
                negative_marks=qdata['neg'],
                explanation=qdata['exp']
            )
            db.session.add(q)
            db.session.flush()

            for opt_idx, (otext, is_cor) in enumerate(qdata['options'], start=1):
                opt = Option(question_id=q.id, option_number=opt_idx, option_text=otext, is_correct=is_cor)
                db.session.add(opt)

        exam2.calculate_total_marks()

        # ------------------------------------------------------------------
        # Examination 3 (TOMORROW): Java Object-Oriented Programming Assessment
        # ------------------------------------------------------------------
        exam3 = Examination(
            college_id=col1.id,
            faculty_id=fac1_profile.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            subject_id=sub_java.id,
            title='Scheduled Assessment: Java Object-Oriented Programming',
            instructions='1. Scheduled for tomorrow morning.\n2. Covers inheritance, polymorphism, abstract classes, and exceptions.\n3. 40 minutes duration.',
            exam_date=tomorrow,
            start_time=time(9, 30),
            end_time=time(11, 30),
            duration_minutes=40,
            passing_percentage=40.0,
            max_attempts=1,
            negative_marking=False,
            negative_mark_value=0.0,
            status='scheduled'
        )
        db.session.add(exam3)
        db.session.flush()

        java_questions = [
            {
                'text': 'Which keyword in Java prevents a class from being subclassed / extended?',
                'marks': 1.0, 'neg': 0.0,
                'exp': 'The "final" keyword declared on a class prevents other classes from inheriting from it.',
                'options': [('static', False), ('abstract', False), ('final', True), ('synchronized', False)]
            },
            {
                'text': 'What is the default value of an uninitialized instance boolean variable in Java?',
                'marks': 1.0, 'neg': 0.0,
                'exp': 'By Java specification, boolean instance fields default to false.',
                'options': [('true', False), ('false', True), ('null', False), ('0', False)]
            },
            {
                'text': 'Which collection interface in Java guarantees unique elements and does not permit duplicates?',
                'marks': 1.0, 'neg': 0.0,
                'exp': 'The Set interface represents a collection that contains no duplicate elements.',
                'options': [('List', False), ('Set', True), ('Queue', False), ('Vector', False)]
            },
            {
                'text': 'What type of exception in Java is checked at compile-time by the Java compiler?',
                'marks': 1.0, 'neg': 0.0,
                'exp': 'Checked exceptions (subclasses of Exception excluding RuntimeException) must be handled or declared.',
                'options': [('NullPointerException', False), ('ArrayIndexOutOfBoundsException', False), ('IOException', True), ('ArithmeticException', False)]
            }
        ]

        for idx, qdata in enumerate(java_questions, start=1):
            q = Question(
                examination_id=exam3.id,
                question_number=idx,
                question_text=qdata['text'],
                marks=qdata['marks'],
                negative_marks=qdata['neg'],
                explanation=qdata['exp']
            )
            db.session.add(q)
            db.session.flush()

            for opt_idx, (otext, is_cor) in enumerate(qdata['options'], start=1):
                opt = Option(question_id=q.id, option_number=opt_idx, option_text=otext, is_correct=is_cor)
                db.session.add(opt)

        exam3.calculate_total_marks()

        # ------------------------------------------------------------------
        # Examination 4 (TOMORROW): Discrete Mathematical Structures Quiz
        # ------------------------------------------------------------------
        exam4 = Examination(
            college_id=col1.id,
            faculty_id=fac1_profile.id,
            course_id=c_btech.id,
            branch_id=b_cse.id,
            semester=3,
            subject_id=sub_math.id,
            title='Scheduled Examination: Discrete Mathematical Structures',
            instructions='1. Scheduled for tomorrow afternoon.\n2. Covers Propositional Logic, Graph Theory, and Pigeonhole Principle.',
            exam_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(16, 0),
            duration_minutes=45,
            passing_percentage=40.0,
            max_attempts=1,
            negative_marking=False,
            negative_mark_value=0.0,
            status='scheduled'
        )
        db.session.add(exam4)
        db.session.flush()

        math_questions = [
            {
                'text': 'In a simple connected undirected planar graph with V vertices and E edges, what does Euler formula state for F faces?',
                'marks': 1.0, 'neg': 0.0,
                'exp': 'Euler formula for planar graphs states: V - E + F = 2.',
                'options': [('V - E + F = 2', True), ('V + E - F = 2', False), ('V + E + F = 0', False), ('V - E - F = 1', False)]
            },
            {
                'text': 'What is the chromatic number of a bipartite graph containing at least one edge?',
                'marks': 1.0, 'neg': 0.0,
                'exp': 'Any bipartite graph with at least one edge can be colored using exactly 2 colors.',
                'options': [('1', False), ('2', True), ('3', False), ('4', False)]
            }
        ]

        for idx, qdata in enumerate(math_questions, start=1):
            q = Question(
                examination_id=exam4.id,
                question_number=idx,
                question_text=qdata['text'],
                marks=qdata['marks'],
                negative_marks=qdata['neg'],
                explanation=qdata['exp']
            )
            db.session.add(q)
            db.session.flush()

            for opt_idx, (otext, is_cor) in enumerate(qdata['options'], start=1):
                opt = Option(question_id=q.id, option_number=opt_idx, option_text=otext, is_correct=is_cor)
                db.session.add(opt)

        exam4.calculate_total_marks()

        # Seed evaluated attempt for Student 2 (Pooja Reddy) on Exam 1
        print("Seeding sample completed attempt for Student 2...")
        att2 = ExamAttempt(
            examination_id=exam1.id,
            student_id=st2_profile.id,
            college_id=col1.id,
            attempt_number=1,
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow() - timedelta(hours=1, minutes=15),
            status='submitted',
            ip_address='127.0.0.1',
            tab_switch_count=0
        )
        db.session.add(att2)
        db.session.flush()

        for idx, q in enumerate(created_ds_questions):
            correct_opt = next(o for o in q.options if o.is_correct)
            wrong_opt = next(o for o in q.options if not o.is_correct)
            chosen_opt = wrong_opt if idx in [8, 9] else correct_opt
            ans = StudentAnswer(
                attempt_id=att2.id,
                question_id=q.id,
                selected_option_id=chosen_opt.id,
                is_marked_for_review=(idx == 2),
                answered_at=datetime.utcnow() - timedelta(hours=1, minutes=20)
            )
            db.session.add(ans)

        res2 = ExamResult(
            attempt_id=att2.id,
            examination_id=exam1.id,
            student_id=st2_profile.id,
            college_id=col1.id,
            total_questions=10,
            correct_answers=8,
            wrong_answers=2,
            unanswered_questions=0,
            total_marks=10.0,
            obtained_marks=7.50,
            percentage=75.0,
            is_passed=True,
            evaluated_at=datetime.utcnow() - timedelta(hours=1, minutes=15)
        )
        db.session.add(res2)

        # ------------------------------------------------------------------
        # Seed Exam 0 Attempts & Finalized Results (Completed Yesterday)
        # Demonstrates Competition Ranking (1, 2, 2, 4) & Real Absent Student
        # ------------------------------------------------------------------
        print("Seeding Exam 0 performance, attendance & tied competition rankings...")

        # 1. Candidate Sneha Patel (Rank 1: 50.0 / 50.0 - 100%)
        att0_sneha = ExamAttempt(
            examination_id=exam0.id, student_id=st4_profile.id, college_id=col1.id,
            attempt_number=1, start_time=datetime.utcnow() - timedelta(days=1, hours=2),
            end_time=datetime.utcnow() - timedelta(days=1, hours=1), status='submitted',
            ip_address='192.168.1.104'
        )
        db.session.add(att0_sneha)
        db.session.flush()
        db.session.add_all([
            StudentAnswer(attempt_id=att0_sneha.id, question_id=q0_1.id, selected_option_id=q0_1.options[2].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=45)),
            StudentAnswer(attempt_id=att0_sneha.id, question_id=q0_2.id, selected_option_id=q0_2.options[0].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=30))
        ])
        res0_sneha = ExamResult(
            attempt_id=att0_sneha.id, examination_id=exam0.id, student_id=st4_profile.id, college_id=col1.id,
            total_questions=2, correct_answers=2, wrong_answers=0, unanswered_questions=0,
            total_marks=50.0, obtained_marks=50.0, percentage=100.0, is_passed=True,
            evaluated_at=datetime.utcnow() - timedelta(days=1, hours=1)
        )
        db.session.add(res0_sneha)

        # 2. Candidate Pooja Reddy (Rank 2: 24.5 / 50.0 - 49%)
        att0_pooja = ExamAttempt(
            examination_id=exam0.id, student_id=st2_profile.id, college_id=col1.id,
            attempt_number=1, start_time=datetime.utcnow() - timedelta(days=1, hours=2),
            end_time=datetime.utcnow() - timedelta(days=1, hours=1, minutes=10), status='submitted',
            ip_address='192.168.1.102'
        )
        db.session.add(att0_pooja)
        db.session.flush()
        db.session.add_all([
            StudentAnswer(attempt_id=att0_pooja.id, question_id=q0_1.id, selected_option_id=q0_1.options[2].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=40)),
            StudentAnswer(attempt_id=att0_pooja.id, question_id=q0_2.id, selected_option_id=q0_2.options[1].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=20))
        ])
        res0_pooja = ExamResult(
            attempt_id=att0_pooja.id, examination_id=exam0.id, student_id=st2_profile.id, college_id=col1.id,
            total_questions=2, correct_answers=1, wrong_answers=1, unanswered_questions=0,
            total_marks=50.0, obtained_marks=24.5, percentage=49.0, is_passed=True,
            evaluated_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=10)
        )
        db.session.add(res0_pooja)

        # 3. Candidate Rahul Sharma (Rank 2 Tied: 24.5 / 50.0 - 49%)
        att0_rahul = ExamAttempt(
            examination_id=exam0.id, student_id=st3_profile.id, college_id=col1.id,
            attempt_number=1, start_time=datetime.utcnow() - timedelta(days=1, hours=2),
            end_time=datetime.utcnow() - timedelta(days=1, hours=1, minutes=15), status='submitted',
            ip_address='192.168.1.103'
        )
        db.session.add(att0_rahul)
        db.session.flush()
        db.session.add_all([
            StudentAnswer(attempt_id=att0_rahul.id, question_id=q0_1.id, selected_option_id=q0_1.options[2].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=42)),
            StudentAnswer(attempt_id=att0_rahul.id, question_id=q0_2.id, selected_option_id=q0_2.options[2].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=25))
        ])
        res0_rahul = ExamResult(
            attempt_id=att0_rahul.id, examination_id=exam0.id, student_id=st3_profile.id, college_id=col1.id,
            total_questions=2, correct_answers=1, wrong_answers=1, unanswered_questions=0,
            total_marks=50.0, obtained_marks=24.5, percentage=49.0, is_passed=True,
            evaluated_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=15)
        )
        db.session.add(res0_rahul)

        # 4. Candidate Vikram Rao (Rank 4: 20.0 / 50.0 - 40%)
        att0_vikram = ExamAttempt(
            examination_id=exam0.id, student_id=st5_profile.id, college_id=col1.id,
            attempt_number=1, start_time=datetime.utcnow() - timedelta(days=1, hours=2),
            end_time=datetime.utcnow() - timedelta(days=1, hours=1, minutes=5), status='submitted',
            ip_address='192.168.1.105'
        )
        db.session.add(att0_vikram)
        db.session.flush()
        db.session.add_all([
            StudentAnswer(attempt_id=att0_vikram.id, question_id=q0_1.id, selected_option_id=q0_1.options[0].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=35)),
            StudentAnswer(attempt_id=att0_vikram.id, question_id=q0_2.id, selected_option_id=q0_2.options[0].id, answered_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=10))
        ])
        res0_vikram = ExamResult(
            attempt_id=att0_vikram.id, examination_id=exam0.id, student_id=st5_profile.id, college_id=col1.id,
            total_questions=2, correct_answers=1, wrong_answers=1, unanswered_questions=0,
            total_marks=50.0, obtained_marks=20.0, percentage=40.0, is_passed=True,
            evaluated_at=datetime.utcnow() - timedelta(days=1, hours=1, minutes=5)
        )
        db.session.add(res0_vikram)

        # 5. Candidate Sai Kumar (st1_profile): Never attempted -> Marked Absent!

        # ---------------------------------------------------------
        # College 2: Apex Institute of Technology
        # ---------------------------------------------------------
        print("Seeding College 2: Apex Institute of Technology...")
        col2 = College(
            name='Apex Institute of Technology',
            code='APEX',
            address='Electronic City Phase 1, Hosur Road, Bengaluru, Karnataka',
            email='contact@apexinstitute.edu',
            contact_number='+91 80 4123 5566',
            logo_filename='default_college_logo.png',
            email_domain='apexinstitute.edu',
            status='active'
        )
        db.session.add(col2)
        db.session.flush()

        adm2_user = User(
            identifier='ADM-APEX-01',
            email='admin@apexinstitute.edu',
            role='college_admin',
            college_id=col2.id,
            is_active=True
        )
        adm2_user.set_password('Password@123')
        db.session.add(adm2_user)
        db.session.flush()

        adm2_profile = CollegeAdminProfile(
            user_id=adm2_user.id,
            admin_id_code='ADM-APEX-01',
            full_name='Dr. K. S. Venkatesh',
            college_id=col2.id,
            contact_number='+91 80 4123 5560'
        )
        adm2_ap = AdminProfile(
            user_id=adm2_user.id,
            admin_id_code='ADM-APEX-01',
            full_name='Dr. K. S. Venkatesh',
            college_id=col2.id,
            contact_number='+91 80 4123 5560',
            registration_status='approved'
        )
        db.session.add_all([adm2_profile, adm2_ap])

        c2_btech = Course(college_id=col2.id, code='BTECH', name='Bachelor of Technology', duration_years=4)
        db.session.add(c2_btech)
        db.session.flush()

        b2_cse = Branch(college_id=col2.id, course_id=c2_btech.id, code='CSE', name='Computer Science & Engineering')
        db.session.add(b2_cse)
        db.session.flush()

        st3_user = User(
            identifier='2025APEX101',
            email='rahul.verma@apexinstitute.edu',
            role='student',
            college_id=col2.id,
            is_active=True
        )
        st3_user.set_password('Password@123')
        db.session.add(st3_user)
        db.session.flush()

        st3_profile = StudentProfile(
            user_id=st3_user.id,
            registration_number='2025APEX101',
            first_name='Rahul',
            last_name='Verma',
            college_id=col2.id,
            course_id=c2_btech.id,
            branch_id=b2_cse.id,
            semester=3,
            academic_year='2026-2027',
            contact_number='+91 99887 76655'
        )
        db.session.add(st3_profile)

        # ---------------------------------------------------------
        # College 3: Metropolitan University
        # ---------------------------------------------------------
        print("Seeding College 3: Metropolitan University...")
        col3 = College(
            name='Metropolitan University of Engineering',
            code='METRO',
            address='Bandra Kurla Complex, Bandra East, Mumbai, Maharashtra',
            email='info@metropolitan.edu',
            contact_number='+91 22 2650 1122',
            logo_filename='default_college_logo.png',
            email_domain='metropolitan.edu',
            status='active'
        )
        db.session.add(col3)
        db.session.flush()

        adm3_user = User(
            identifier='ADM-METRO-01',
            email='admin@metropolitan.edu',
            role='college_admin',
            college_id=col3.id,
            is_active=True
        )
        adm3_user.set_password('Password@123')
        db.session.add(adm3_user)
        db.session.flush()

        adm3_profile = CollegeAdminProfile(
            user_id=adm3_user.id,
            admin_id_code='ADM-METRO-01',
            full_name='Dr. Meenakshi Joshi',
            college_id=col3.id,
            contact_number='+91 22 2650 1120'
        )
        adm3_ap = AdminProfile(
            user_id=adm3_user.id,
            admin_id_code='ADM-METRO-01',
            full_name='Dr. Meenakshi Joshi',
            college_id=col3.id,
            contact_number='+91 22 2650 1120',
            registration_status='approved'
        )
        db.session.add_all([adm3_profile, adm3_ap])

        db.session.commit()
        print("\nDatabase initialization & multi-subject scheduled seeding complete!")

if __name__ == '__main__':
    seed()

# Multi-College Online Examination Management System

An enterprise-grade, multi-tenant university examination management platform built with Python, Flask, Flask-SQLAlchemy, and ReportLab. It allows multiple independent colleges to conduct scheduled, computer-based tests (CBT) with automated server-side evaluation, real-time proctoring telemetry, role-based data isolation, and instant official PDF scorecard generation.

---

## 1. Updated 2-Screen Academic Architecture

1. **Screen 1 — Initial Institutional Login (`/` & `/auth/login`):**
   - The primary entry point of the website.
   - Prompts strictly for **Registration Number / User ID** and **Password**.
   - Authenticates against the relational database and automatically detects the student's registered college.

2. **Screen 2 — Academic Workspace & Course/Subject Gateway (`/portal/workspace`):**
   - Opens immediately upon successful authentication.
   - Displays verified candidate credentials, institutional crest, college code, degree program, branch, and semester.
   - **Course & Subject Selector:** Allows students and faculty to select their active course paper and subject to launch matching examinations.
   - **Quick 1-Click Evaluation Access:** Dedicated demonstration panel with master credentials (`Password@123`) and instant role switchers.

3. **Student Examination Portal (`/student/dashboard`):**
   - Displays candidate registration number, enrolled degree program, branch, and semester.
   - Summary performance tiles:
     - **Available Examinations Today** (Active sessions ready to take).
     - **Scheduled Examinations Tomorrow** (Upcoming examination papers).
     - **Completed Evaluations** (Graded records).
     - **Overall Average Score** (Cumulative percentage).
   - **Subject Filter Bar:** Filter examinations and question papers by enrolled curriculum subjects (Data Structures, DBMS, Java OOP, Discrete Math).
   - **Start Examination:** Launches the CBT interface with questions specific to the selected subject.

4. **Faculty Assessment Workspace (`/faculty/dashboard`):**
   - Course and Subject selector to inspect the complete question bank for any curriculum paper.
   - Displays exact question stems, multiple-choice options, correct answer keys, and faculty explanations/solutions.
   - Live Chart.js candidate score distributions and accuracy statistics.

5. **College Administration Console (`/college-admin/dashboard`):**
   - Course and Subject catalog filtering.
   - Program definitions (B.Tech, MCA), departmental branches (CSE, ECE), and semester subject rosters.

---

## 2. Technology Stack

- **Backend:** Python 3, Flask 3.x, Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF Protection), Werkzeug (Password Hashing).
- **Database:** SQLite (PostgreSQL-compatible relational schema with foreign keys, indexes, and unique constraints).
- **Frontend:** HTML5, CSS3 (Professional Navy/Slate University Theme), Vanilla JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons.
- **Analytics & PDF:** Chart.js 4.x (Distribution & accuracy charts), ReportLab 5.x (PDF scorecards).
- **Testing:** Pytest 8.x test suite covering authentication, multi-tenancy, exam execution, evaluation, and security.

---

## 3. Demonstration Credentials

All seeded test accounts use the password: `Password@123`

| Role | User Identifier | Email | Institution Affiliation | Description / Workflow |
| :--- | :--- | :--- | :--- | :--- |
| **Student (Candidate 1)** | `2025DAMBT11765` | `sai.kumar@abccollege.edu` | ABC Engineering College | Enrolled in B.Tech CSE Sem 3. Active Data Structures and DBMS exams available today. |
| **Student (Candidate 2)** | `2025DAMBT11766` | `pooja.reddy@abccollege.edu` | ABC Engineering College | Completed examination attempt ready to inspect scorecard and download ReportLab PDF. |
| **Student (College 2)** | `2025APEX101` | `rahul.verma@apexinstitute.edu` | Apex Institute of Tech | Demonstrates automatic college identification for a second independent college. |
| **Faculty Member** | `FAC-ABC-01` | `anita.sharma@abccollege.edu` | ABC Engineering College | Select courses & subjects to view question banks, answer keys, solutions, and analytics. |
| **College Admin** | `ADM-ABC-01` | `admin@abccollege.edu` | ABC Engineering College | College catalog, courses, branches, curriculum subjects, student enrollment, faculty roster. |
| **Super Admin** | `SUPERADMIN` | `superadmin@university.edu` | Global Platform | University central control, college registrations, approval, logo upload, user directory. |

---

## 4. Live Server Execution

To run the live server locally:
```powershell
cd "c:\Users\velpu\OneDrive\Attachments\Desktop\anti IDE\online-examination-system"
..\venv\Scripts\python run.py
```
Server runs on: `http://127.0.0.1:5000`

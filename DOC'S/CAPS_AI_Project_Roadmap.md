# 🚀 CAPS AI

## Complete Project Development Roadmap

**Tech Stack:** React + FastAPI + MongoDB + OpenAI + scikit-learn

------------------------------------------------------------------------

# 📌 1. Project Overview

CAPS AI is an AI-assisted academic evaluation and plagiarism monitoring
system designed to:

-   Standardize 40 internal + 60 final marking scheme
-   Assist teachers with AI-based report evaluation
-   Detect cross-section plagiarism using TF-IDF + Cosine Similarity
-   Provide analytics for teachers and admin
-   Maintain audit logs for academic integrity
-   Flag academically at-risk students

------------------------------------------------------------------------

# 🎯 2. Project Objectives

-   Ensure fair and transparent internal evaluation
-   Reduce manual errors in marking
-   Assist teachers using AI-generated feedback
-   Maintain academic integrity using similarity detection
-   Provide performance insights through analytics dashboards

------------------------------------------------------------------------

# 👥 3. Project Roles & Responsibilities

## 🔹 Admin

-   Manage teachers and students
-   Create sections and subjects
-   Assign teachers to section-subjects
-   View analytics dashboards
-   View audit logs
-   Monitor academic risk flags

## 🔹 Teacher

-   Create assignments
-   Set deadlines
-   Review AI-suggested report marks
-   Enter attendance, skill, behavior, viva, and final exam marks
-   Review similarity alerts
-   Finalize student evaluations

## 🔹 Student

-   Upload assignments
-   View internal and final marks
-   View AI-generated feedback
-   Download PDF performance report

------------------------------------------------------------------------

# 🏗 4. System Architecture

Frontend (React)\
↓\
FastAPI Backend (Python)\
↓\
MongoDB Database\
↓\
AI (OpenAI API)\
↓\
Similarity Engine (scikit-learn)

------------------------------------------------------------------------

# 🛠 5. Tech Stack

## Frontend

-   React.js (Vite recommended)
-   Tailwind CSS
-   Axios
-   Recharts
-   React Router

## Backend

-   FastAPI
-   Uvicorn
-   Motor (MongoDB async driver)
-   Pydantic
-   Passlib (bcrypt)
-   python-jose (JWT)

## AI & NLP

-   OpenAI Python SDK
-   scikit-learn (TF-IDF + cosine similarity)
-   NLTK (optional)

## File Handling

-   python-multipart
-   pdfplumber
-   python-docx

## PDF Generation

-   ReportLab

------------------------------------------------------------------------

# 🗄 6. Database Schema Collections

-   Users\
-   Sections\
-   Students\
-   Subjects\
-   SectionSubjects\
-   Assignments\
-   Submissions\
-   Evaluations\
-   SimilarityLogs\
-   Notifications\
-   AuditLogs

------------------------------------------------------------------------

# 📊 7. Evaluation Structure

## Internal = 40 Marks

-   Attendance (5)
-   Skill (2.5)
-   Behavior (2.5)
-   Report/File (10)
-   Viva (20)

## Final Exam = 60 Marks

## Attendance Calculation

95--100 → 5\
90--94 → 4\
85--89 → 3\
80--84 → 2\
70--79 → 1\
\<70 → 0

## Grade Logic

90--100 → A+\
80--89 → A\
70--79 → B\
60--69 → C\
\<60 → Needs Improvement

------------------------------------------------------------------------

# 🤖 8. AI Evaluation Flow

1.  Student uploads report
2.  Extract text
3.  Send to OpenAI API
4.  Receive:
    -   Suggested marks (out of 10)
    -   Strengths
    -   Weaknesses
    -   Improvement suggestions
5.  Teacher confirms final marks

------------------------------------------------------------------------

# 🚨 9. Similarity Detection Flow

1.  Preprocess text
2.  TF-IDF vectorization
3.  Cosine similarity comparison
4.  If score \> threshold:
    -   Create SimilarityLog
    -   Notify teacher(s)
    -   Flag submissions

------------------------------------------------------------------------

# 📅 10. Development Timeline (10 Weeks)

Week 1: Project setup (FastAPI + React + MongoDB)\
Week 2: Authentication & Role system\
Week 3: Section & Subject management\
Week 4: Assignment module & file upload\
Week 5: Evaluation logic implementation\
Week 6: Similarity engine integration\
Week 7: AI integration\
Week 8: Analytics dashboard\
Week 9: PDF report generation\
Week 10: Testing & optimization

------------------------------------------------------------------------

# 🔐 11. Security & Compliance

-   Password hashing (bcrypt)
-   JWT authentication
-   Role-based authorization
-   File validation & size limits
-   Input sanitization
-   Audit logging for changes

------------------------------------------------------------------------

# 📦 12. Final Deliverables

-   Fully functional web application
-   AI-based report evaluation
-   Cross-section plagiarism detection
-   Analytics dashboards
-   Audit tracking system
-   PDF report generation
-   Complete project documentation

------------------------------------------------------------------------

# 🎓 Project Outcome

✔ AI-integrated academic system\
✔ Transparent evaluation process\
✔ Academic integrity monitoring\
✔ Data-driven performance insights\
✔ Placement-ready portfolio project

------------------------------------------------------------------------

# 🚀 Ready for Development

Start with Backend Setup → Authentication → Academic Structure →
Assignment → AI → Similarity → Analytics → Testing

# TAPA - Tool for Automated Personalised Assessment

TAPA is an AI-powered student revision web application developed as a Final Year Project prototype. The system helps students convert their uploaded lecture materials into reviewed learning content, generated multiple-choice questions, quiz attempts, saved history, and personal study notes.

The main goal of TAPA is to support active revision. Instead of only re-reading notes, students can upload their own materials, review the extracted text, generate MCQs, attempt quizzes by difficulty level, and write notes based on generated questions and explanations.

---

## 1. Main Features

### User Account and Profile

- User registration, login, and logout
- Profile-first onboarding flow
- Student profile setup before using the main system
- Change password feature for logged-in users
- User-owned materials, quiz attempts, and notes

### Material Upload and Review

- Upload up to 3 files for one revision material
- Supported file formats:
  - PDF
  - DOCX
  - PPTX
  - HTML
- Extract text from uploaded files
- Review extracted text before quiz generation
- AI Clean Text function to improve messy extracted content
- Upload disclaimer to remind users to upload only appropriate learning materials

### AI Quiz Generation

- Generate MCQs from reviewed lecture content
- Uses Gemini API for AI-powered text cleaning and MCQ generation
- Quiz preference options:
  - Number of questions
  - Difficulty level
  - Question style
  - Quiz focus
- Supported difficulty levels:
  - Hot
  - Moderate
  - Cold
  - All / Mixed Difficulty
- Regenerate confirmation page to avoid accidental replacement of generated questions

### Quiz Practice

- Interactive quiz answering flow
- One-question-at-a-time quiz interface
- Answer checking before continuing
- Correct answer and explanation display
- Live quiz timer display
- Quiz duration tracking saved with attempts
- Retry wrong questions feature

### History and Review

- Global quiz history page
- Material-specific attempt history page
- Attempt detail page showing selected answer, correct answer, and explanation
- Saved result records with score, percentage, level, attempt type, date, and time used
- Question bank page for generated questions
- Question bank export as text file

### Study Notes

- Notes Library for uploaded materials
- Material-specific notes page
- Generated questions and explanations shown beside the notes editor
- Rich text note editor with text color options:
  - Black
  - Blue
  - Red
- Notes are linked to the user's own material

### Material Management

- Dashboard showing uploaded materials
- Pin / favourite material feature
- Material workspace page
- Delete material with related data
- Delete quiz attempts

### Onboarding and UI Support

- Getting Started checklist for first-time users
- Current-step highlight to guide new users
- Completion congratulations card after the first full TAPA learning flow
- Loading overlay for AI actions
- Cleaner interface for material workspace, quiz attempts, notes, login, and register pages

### Admin Course Style Tool

- Admin-only Course Style access
- Course Style page is hidden from normal users
- Direct access to Course Style is blocked for non-admin users
- Admin can generate a course style profile from reference past papers

---

## 2. Technology Stack

### Backend

- Python
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-Migrate
- SQLAlchemy
- PyMySQL

### Database

- MySQL / MariaDB
- WAMPServer is used for local development database hosting

### AI Service

- Google Gemini API
- `google-genai` Python package

### File Processing

- PyMuPDF for PDF processing
- python-docx for DOCX processing
- python-pptx for PPTX processing
- BeautifulSoup for HTML processing

### Frontend

- HTML
- CSS
- Jinja2 templates

---

## 3. Project Structure

```text
tapafyp/
│
├── app/
│   ├── auth/
│   │   └── routes.py
│   │
│   ├── services/
│   │   ├── ai_service.py
│   │   ├── course_profile_service.py
│   │   └── lecture_file_service.py
│   │
│   ├── static/
│   │   └── css/
│   │       └── style.css
│   │
│   ├── templates/
│   │   ├── components/
│   │   │   └── onboarding_checklist.html
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── material_review.html
│   │   ├── material_detail.html
│   │   ├── question_bank.html
│   │   ├── choose_level.html
│   │   ├── quiz_question.html
│   │   ├── quiz_result.html
│   │   ├── history.html
│   │   ├── material_attempts.html
│   │   ├── attempt_detail.html
│   │   ├── notes_library.html
│   │   ├── material_notes.html
│   │   ├── profile.html
│   │   └── course_style.html
│   │
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
│
├── migrations/
├── past_papers/
├── uploads/
├── config.py
├── requirements.txt
├── run.py
├── .env.example
└── README.md
```

---

## 4. Environment Variables

Create a `.env` file in the project root based on `.env.example`.

Example:

```env
SECRET_KEY=replace-with-your-secret-key
DATABASE_URL=mysql+pymysql://root:@localhost:3306/tapa_db
GEMINI_API_KEY=replace-with-your-gemini-api-key
```

Important:

```text
Do not commit the real .env file.
Do not expose the Gemini API key.
Only commit .env.example.
```

---

## 5. Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/lexusKY/tapafyp.git
cd tapafyp
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment.

For Windows:

```bash
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create the Database

Start WAMPServer and make sure MySQL/MariaDB is running.

Create a database named:

```text
tapa_db
```

### Step 5: Configure `.env`

Create a `.env` file in the project root.

Example:

```env
SECRET_KEY=replace-with-your-secret-key
DATABASE_URL=mysql+pymysql://root:@localhost:3306/tapa_db
GEMINI_API_KEY=replace-with-your-gemini-api-key
```

If `localhost` does not work, try:

```env
DATABASE_URL=mysql+pymysql://root:@127.0.0.1:3306/tapa_db
```

### Step 6: Run Database Migrations

```bash
flask db upgrade
```

During development, if a new migration is needed:

```bash
flask db migrate -m "migration message"
flask db upgrade
```

### Step 7: Run the Application

```bash
python run.py
```

Open the application in a browser:

```text
http://127.0.0.1:5000
```

---

## 6. Admin Access for Course Style

The Course Style page is restricted to admin users only.

By default, users are normal users. To make an account an admin, update the `users` table in the database:

```text
is_admin = 1
```

For normal users:

```text
is_admin = 0
```

Admin users can access:

```text
/course-style
```

Normal users cannot see the Course Style link and will be redirected if they try to access the page directly.

---

## 7. Course Style Folder Structure

Course style profiles are stored under the `past_papers` folder.

Example structure:

```text
past_papers/
└── UECS3253/
    ├── archive/
    ├── main_reference/
    │   ├── past_paper_2023.pdf
    │   └── past_paper_2024.pdf
    ├── support_reference/
    └── style_profile.txt
```

The Course Style tool reads PDF files from:

```text
past_papers/<COURSE_CODE>/main_reference/
```

and generates:

```text
past_papers/<COURSE_CODE>/style_profile.txt
```

The style profile helps TAPA generate questions that better follow the expected course style. However, it is not a full course-authenticity verification system.

---

## 8. Recommended User Flow

```text
Register
→ Login
→ Complete Profile
→ Upload Lecture Material
→ Review Extracted Text
→ Optional AI Clean Text
→ Set Quiz Preferences
→ Generate Quiz
→ Choose Difficulty Level
→ Attempt Quiz
→ View Result and Explanation
→ Create Study Notes
→ Review History / Notes Later
```

The first-time user flow is supported by the Getting Started checklist.

---

## 9. AI Generation Notes

TAPA uses Gemini API to assist with:

- Cleaning extracted lecture text
- Generating MCQs
- Generating hints and explanations
- Assigning difficulty levels
- Creating course style profiles for admin use

Generated question quality depends on:

- Quality of uploaded files
- Accuracy of extracted text
- User-reviewed cleaned text
- Quiz focus settings
- Availability and quality of course style profiles

Users are encouraged to review extracted text before generating quizzes.

---

## 10. Security and Safety Notes

TAPA includes several prototype-level safeguards:

- Users must log in before accessing materials, quizzes, notes, and history
- Users can only access their own uploaded materials
- Users can only access their own quiz attempts
- Course Style is restricted to admin users
- Uploaded filenames are processed using secure filename handling
- File upload size is limited through Flask configuration
- Users are reminded not to upload private, sensitive, inappropriate, illegal, or unrelated content
- AI prompts include instructions to treat uploaded text as content, not as commands
- Regenerate confirmation prevents accidental replacement of generated questions
- Passwords are stored as hashed values

Important:

```text
The real .env file must not be committed.
The Gemini API key must not be exposed publicly.
```

---

## 11. Known Limitations

TAPA is a Final Year Project prototype, not a production deployment. Some limitations remain:

- The system cannot perfectly verify whether uploaded content truly belongs to the selected course
- A user may still upload unrelated content under a valid course code
- Course Style helps guide generation style, but it does not fully authenticate uploaded materials
- AI-generated questions may still require user review
- There is no production-level rate limiting for Gemini API usage
- There is no email-based password reset
- Rich text notes use basic sanitisation only and may need stronger production-grade HTML sanitisation
- Content safety and course relevance checking can be improved further

These limitations are acceptable for a prototype but should be addressed before production use.

---

## 12. Future Enhancements

Possible future improvements include:

- AI-based course relevance classification
- Similarity comparison against lecturer-approved course materials
- Automatic course keyword generation
- Admin dashboard for monitoring usage
- Daily AI generation quota per user
- Email-based forgot password flow
- More advanced study notes editor
- Drawing or sketching tools for notes
- Export notes to PDF
- More detailed quiz analytics
- Cloud deployment
- Stronger content moderation and file validation

---

## 13. Final Project Summary

TAPA provides a complete AI-supported revision workflow:

```text
Upload material
→ Review extracted text
→ Generate quiz
→ Attempt quiz
→ Review result
→ Save study notes
→ Track learning history
```

The system is designed for student-centred revision and demonstrates the use of AI to support active learning through personalised quiz generation and learning reflection.

# TAPA - Tool for Automated Personalised Assessment

TAPA is an AI-powered student revision web application that converts uploaded lecture materials into interactive quiz practice. The system allows students to upload learning materials, review and clean extracted text, generate multiple-choice questions, attempt quizzes by difficulty level, save quiz history, and write personal study notes.

This project was developed as a Final Year Project system prototype.

---

## 1. Main Features

### User Account and Profile

- User registration, login, and logout
- Student profile setup
- Profile-first onboarding flow
- Change password feature for logged-in users

### Material Upload and Review

- Upload up to 3 files for one revision set
- Supported formats: PDF, DOCX, PPTX, and HTML
- Extract text from uploaded files
- Review extracted text before quiz generation
- AI clean text function for messy extracted notes

### AI Quiz Generation

- Generate multiple-choice questions from reviewed lecture content
- Uses Gemini API for AI-powered text cleaning and MCQ generation
- Supports quiz preferences:
  - Number of questions
  - Difficulty
  - Question style
  - Quiz focus
- Difficulty levels:
  - Hot
  - Moderate
  - Cold
  - All / Mixed Difficulty
- Regenerate confirmation page to prevent accidental replacement of generated questions

### Quiz Practice

- Interactive quiz answering flow
- Immediate answer checking
- Correct answer and explanation display
- Quiz progress indicator
- Time used tracking
- Retry wrong questions

### Quiz History and Review

- Global quiz history page
- Material-specific attempt history
- Saved result detail page
- Score, percentage, level, attempt type, date, and time used
- Question bank page
- Question bank export to text file

### Study Notes

- Notes library for uploaded materials
- Material-specific study notes page
- Generated questions and explanations shown beside the notes editor
- Rich text note editor with text colour options:
  - Black
  - Blue
  - Red

### Material Management

- Dashboard with uploaded materials
- Pin / favourite materials
- View material workspace
- Delete materials and related data
- Delete quiz attempts

### Onboarding and UI Support

- Getting Started checklist for first-time users
- Completion congratulations card after the full learning flow is completed
- Loading overlay for AI actions
- Admin-only Course Style page access

### Admin Course Style Tool

- Admin-only access
- Course Style tool can analyse past paper folders and generate a style profile
- Normal users cannot access the Course Style page directly

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

- Google Gemini API using `google-genai`

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
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── material_review.html
│   │   ├── material_detail.html
│   │   ├── choose_level.html
│   │   ├── quiz_question.html
│   │   ├── quiz_result.html
│   │   ├── history.html
│   │   ├── material_attempts.html
│   │   ├── attempt_detail.html
│   │   ├── notes_library.html
│   │   ├── material_notes.html
│   │   ├── profile.html
│   │   ├── login.html
│   │   ├── register.html
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
Do not commit your real .env file.
Do not expose your Gemini API key.
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

For macOS/Linux:

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up the Database

Start WAMPServer and make sure MySQL/MariaDB is running.

Create a database named:

```text
tapa_db
```

Then create a `.env` file using `.env.example`.

Example:

```env
SECRET_KEY=replace-with-your-secret-key
DATABASE_URL=mysql+pymysql://root:@localhost:3306/tapa_db
GEMINI_API_KEY=replace-with-your-gemini-api-key
```

### Step 5: Run Database Migrations

```bash
flask db upgrade
```

If migrations need to be created during development:

```bash
flask db migrate -m "migration message"
flask db upgrade
```

### Step 6: Run the Application

```bash
python run.py
```

Open the system in a browser:

```text
http://127.0.0.1:5000
```

---

## 6. Admin Access for Course Style

The Course Style page is restricted to admin users only.

By default, new users are normal users.

To make an account admin, update the `users` table in the database:

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

Normal users will be redirected away if they try to access it directly.

---

## 7. Recommended User Flow

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

---

## 8. Notes About AI Generation

TAPA uses AI to assist with:

- Cleaning extracted lecture text
- Generating multiple-choice questions
- Creating hints and explanations
- Assigning difficulty levels

The quality of generated questions depends on:

- Quality of extracted text
- Clarity of uploaded materials
- User-reviewed cleaned text
- Quiz focus and preference settings

Users are encouraged to review extracted text before generating quizzes.

---

## 9. Security Notes

- Passwords are stored as hashed values.
- Users must log in before accessing materials, quizzes, notes, or history.
- Users can only access their own uploaded materials and quiz attempts.
- Course Style tools are restricted to admin users.
- The real `.env` file should not be committed to GitHub.

---

## 10. Future Enhancements

Possible future improvements include:

- Real email-based password reset
- More advanced note editor tools
- Drawing or sketching tools for study notes
- More detailed quiz analytics
- Export notes to PDF
- More file type support
- Deployment to a cloud hosting platform
- Advanced admin dashboard

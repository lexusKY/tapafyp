import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, session
from flask_login import login_required, current_user

from app import db
from app.models import Material, Question, Choice
from app.services.ai_service import generate_mcqs_from_text
from app.services.course_profile_service import build_style_profile_for_course
from app.services.lecture_file_service import extract_text_from_file, combine_extracted_text

main = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "html"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_style_profile(course_code, base_path):
    if not course_code:
        return None

    profile_path = os.path.join(base_path, course_code.upper(), "style_profile.txt")

    if not os.path.exists(profile_path):
        return None

    with open(profile_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_filtered_questions(material_id, level):
    query = Question.query.filter_by(material_id=material_id)

    if level and level != "All":
        query = query.filter_by(difficulty=level)

    return query.order_by(Question.id.asc()).all()


def get_retry_questions(material_id, level):
    session_key = f"retry_{material_id}_{level}_question_ids"
    question_ids = session.get(session_key, [])

    if not question_ids:
        return []

    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    question_map = {q.id: q for q in questions}

    ordered_questions = [question_map[qid] for qid in question_ids if qid in question_map]
    return ordered_questions


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/dashboard")
@login_required
def dashboard():
    materials = Material.query.order_by(Material.id.desc()).all()
    return render_template("dashboard.html", user=current_user, materials=materials)


@main.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        course_code = request.form.get("course_code", "").strip().upper()

        if not title:
            flash("Please enter a title.", "danger")
            return redirect(url_for("main.upload"))

        if not course_code:
            flash("Please enter a course code.", "danger")
            return redirect(url_for("main.upload"))

        uploaded_files = request.files.getlist("note_files")
        valid_files = [f for f in uploaded_files if f and f.filename.strip()]

        if not valid_files:
            flash("Please upload at least 1 file.", "danger")
            return redirect(url_for("main.upload"))

        if len(valid_files) > 3:
            flash("You can upload a maximum of 3 files only.", "danger")
            return redirect(url_for("main.upload"))

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        gemini_api_key = current_app.config.get("GEMINI_API_KEY")

        saved_filenames = []
        file_results = []

        for file in valid_files:
            if not allowed_file(file.filename):
                flash("Only PDF, DOCX, PPTX, and HTML files are allowed.", "danger")
                return redirect(url_for("main.upload"))

            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            extension = filename.rsplit(".", 1)[1].lower()
            extracted_text = extract_text_from_file(file_path, extension, gemini_api_key)

            saved_filenames.append(filename)
            file_results.append({
                "filename": filename,
                "text": extracted_text
            })

        combined_text = combine_extracted_text(file_results)
        combined_filename_text = ", ".join(saved_filenames)

        new_material = Material(
            course_code=course_code,
            title=title,
            filename=combined_filename_text,
            extracted_text=combined_text
        )

        db.session.add(new_material)
        db.session.commit()

        flash("Lecture files uploaded and processed successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("upload.html")


@main.route("/material/<int:material_id>")
@login_required
def view_material(material_id):
    material = Material.query.get_or_404(material_id)
    return render_template("material_detail.html", material=material)


@main.route("/generate-quiz/<int:material_id>", methods=["POST"])
@login_required
def generate_quiz(material_id):
    material = Material.query.get_or_404(material_id)

    if not material.extracted_text:
        flash("This material has no extracted text to generate questions from.", "warning")
        return redirect(url_for("main.dashboard"))

    gemini_api_key = current_app.config.get("GEMINI_API_KEY")
    if not gemini_api_key:
        flash("Gemini API key is missing.", "danger")
        return redirect(url_for("main.dashboard"))

    style_profile_text = load_style_profile(
        material.course_code,
        current_app.config["PAST_PAPERS_FOLDER"]
    )

    old_questions = Question.query.filter_by(material_id=material.id).all()

    for question in old_questions:
        Choice.query.filter_by(question_id=question.id).delete()

    Question.query.filter_by(material_id=material.id).delete()
    db.session.commit()

    generated_questions = generate_mcqs_from_text(
        material.extracted_text,
        gemini_api_key,
        course_code=material.course_code,
        style_profile_text=style_profile_text
    )

    if not generated_questions:
        flash("Failed to generate quiz questions.", "danger")
        return redirect(url_for("main.dashboard"))

    for q in generated_questions:
        new_question = Question(
            material_id=material.id,
            question_text=q["question_text"],
            difficulty=q["difficulty"]
        )
        db.session.add(new_question)
        db.session.flush()

        for c in q["choices"]:
            new_choice = Choice(
                question_id=new_question.id,
                choice_text=c["choice_text"],
                is_correct=c["is_correct"]
            )
            db.session.add(new_choice)

    db.session.commit()

    flash("Interactive quiz generated successfully.", "success")
    return redirect(url_for("main.choose_level", material_id=material.id))


@main.route("/choose-level/<int:material_id>")
@login_required
def choose_level(material_id):
    material = Material.query.get_or_404(material_id)
    questions = Question.query.filter_by(material_id=material.id).all()

    if not questions:
        flash("No quiz questions generated yet.", "warning")
        return redirect(url_for("main.dashboard"))

    hot_count = Question.query.filter_by(material_id=material.id, difficulty="Hot").count()
    moderate_count = Question.query.filter_by(material_id=material.id, difficulty="Moderate").count()
    cold_count = Question.query.filter_by(material_id=material.id, difficulty="Cold").count()
    all_count = len(questions)

    return render_template(
        "choose_level.html",
        material=material,
        hot_count=hot_count,
        moderate_count=moderate_count,
        cold_count=cold_count,
        all_count=all_count
    )


@main.route("/start-quiz/<int:material_id>/<level>")
@login_required
def start_quiz(material_id, level):
    material = Material.query.get_or_404(material_id)
    questions = get_filtered_questions(material.id, level)

    if not questions:
        flash(f"No {level} questions available for this quiz.", "warning")
        return redirect(url_for("main.choose_level", material_id=material.id))

    session[f"quiz_{material_id}_{level}_answers"] = {}
    session.pop(f"retry_{material_id}_{level}_question_ids", None)
    session.pop(f"retry_{material_id}_{level}_answers", None)

    return redirect(url_for("main.quiz_question", material_id=material.id, level=level, question_number=1))


@main.route("/quiz/<int:material_id>/<level>/<int:question_number>", methods=["GET", "POST"])
@login_required
def quiz_question(material_id, level, question_number):
    material = Material.query.get_or_404(material_id)
    questions = get_filtered_questions(material.id, level)

    if not questions:
        flash("No quiz questions found.", "warning")
        return redirect(url_for("main.dashboard"))

    total_questions = len(questions)

    if question_number < 1 or question_number > total_questions:
        return redirect(url_for("main.quiz_result", material_id=material.id, level=level))

    current_question = questions[question_number - 1]
    session_key = f"quiz_{material_id}_{level}_answers"
    answers = session.get(session_key, {})

    if request.method == "POST":
        selected_choice_id = request.form.get("selected_choice")

        if not selected_choice_id:
            flash("Please select an answer before continuing.", "warning")
            return redirect(url_for("main.quiz_question", material_id=material.id, level=level, question_number=question_number))

        answers[str(current_question.id)] = int(selected_choice_id)
        session[session_key] = answers

        next_question_number = question_number + 1

        if next_question_number > total_questions:
            return redirect(url_for("main.quiz_result", material_id=material.id, level=level))

        return redirect(url_for("main.quiz_question", material_id=material.id, level=level, question_number=next_question_number))

    selected_answer = answers.get(str(current_question.id))

    return render_template(
        "quiz_question.html",
        material=material,
        question=current_question,
        question_number=question_number,
        total_questions=total_questions,
        selected_answer=selected_answer,
        level=level
    )


@main.route("/quiz-result/<int:material_id>/<level>")
@login_required
def quiz_result(material_id, level):
    material = Material.query.get_or_404(material_id)
    questions = get_filtered_questions(material.id, level)

    session_key = f"quiz_{material_id}_{level}_answers"
    answers = session.get(session_key, {})

    score = 0
    results = []
    wrong_question_ids = []

    for question in questions:
        correct_choice = Choice.query.filter_by(question_id=question.id, is_correct=True).first()
        selected_choice_id = answers.get(str(question.id))
        selected_choice = Choice.query.get(selected_choice_id) if selected_choice_id else None

        is_correct = (
            selected_choice is not None and
            correct_choice is not None and
            selected_choice.id == correct_choice.id
        )

        if is_correct:
            score += 1
        else:
            wrong_question_ids.append(question.id)

        results.append({
            "question": question,
            "selected_choice": selected_choice,
            "correct_choice": correct_choice,
            "is_correct": is_correct
        })

    total_questions = len(questions)
    retry_available = len(wrong_question_ids) > 0

    session[f"retry_{material_id}_{level}_question_ids"] = wrong_question_ids

    return render_template(
        "quiz_result.html",
        material=material,
        score=score,
        total_questions=total_questions,
        results=results,
        level=level,
        retry_available=retry_available
    )


@main.route("/retry-wrong/<int:material_id>/<level>")
@login_required
def retry_wrong(material_id, level):
    material = Material.query.get_or_404(material_id)
    questions = get_retry_questions(material.id, level)

    if not questions:
        flash("No wrong questions available to retry.", "warning")
        return redirect(url_for("main.quiz_result", material_id=material.id, level=level))

    session[f"retry_{material_id}_{level}_answers"] = {}
    return redirect(url_for("main.retry_question", material_id=material.id, level=level, question_number=1))


@main.route("/retry-quiz/<int:material_id>/<level>/<int:question_number>", methods=["GET", "POST"])
@login_required
def retry_question(material_id, level, question_number):
    material = Material.query.get_or_404(material_id)
    questions = get_retry_questions(material.id, level)

    if not questions:
        flash("No retry questions found.", "warning")
        return redirect(url_for("main.dashboard"))

    total_questions = len(questions)

    if question_number < 1 or question_number > total_questions:
        return redirect(url_for("main.retry_result", material_id=material.id, level=level))

    current_question = questions[question_number - 1]
    session_key = f"retry_{material_id}_{level}_answers"
    answers = session.get(session_key, {})

    if request.method == "POST":
        selected_choice_id = request.form.get("selected_choice")

        if not selected_choice_id:
            flash("Please select an answer before continuing.", "warning")
            return redirect(url_for("main.retry_question", material_id=material.id, level=level, question_number=question_number))

        answers[str(current_question.id)] = int(selected_choice_id)
        session[session_key] = answers

        next_question_number = question_number + 1

        if next_question_number > total_questions:
            return redirect(url_for("main.retry_result", material_id=material.id, level=level))

        return redirect(url_for("main.retry_question", material_id=material.id, level=level, question_number=next_question_number))

    selected_answer = answers.get(str(current_question.id))

    return render_template(
        "quiz_question.html",
        material=material,
        question=current_question,
        question_number=question_number,
        total_questions=total_questions,
        selected_answer=selected_answer,
        level=f"{level} Retry"
    )


@main.route("/retry-result/<int:material_id>/<level>")
@login_required
def retry_result(material_id, level):
    material = Material.query.get_or_404(material_id)
    questions = get_retry_questions(material.id, level)

    session_key = f"retry_{material_id}_{level}_answers"
    answers = session.get(session_key, {})

    score = 0
    results = []

    for question in questions:
        correct_choice = Choice.query.filter_by(question_id=question.id, is_correct=True).first()
        selected_choice_id = answers.get(str(question.id))
        selected_choice = Choice.query.get(selected_choice_id) if selected_choice_id else None

        is_correct = (
            selected_choice is not None and
            correct_choice is not None and
            selected_choice.id == correct_choice.id
        )

        if is_correct:
            score += 1

        results.append({
            "question": question,
            "selected_choice": selected_choice,
            "correct_choice": correct_choice,
            "is_correct": is_correct
        })

    total_questions = len(questions)

    return render_template(
        "quiz_result.html",
        material=material,
        score=score,
        total_questions=total_questions,
        results=results,
        level=f"{level} Retry",
        retry_available=False
    )


@main.route("/course-style")
@login_required
def course_style_page():
    return render_template("course_style.html")


@main.route("/generate-style-profile", methods=["POST"])
@login_required
def generate_style_profile_route():
    course_code = request.form.get("course_code", "").strip().upper()

    if not course_code:
        flash("Please enter a course code.", "danger")
        return redirect(url_for("main.course_style_page"))

    gemini_api_key = current_app.config.get("GEMINI_API_KEY")
    if not gemini_api_key:
        flash("Gemini API key is missing.", "danger")
        return redirect(url_for("main.course_style_page"))

    base_path = current_app.config["PAST_PAPERS_FOLDER"]

    success, result = build_style_profile_for_course(course_code, base_path, gemini_api_key)

    if success:
        flash(f"Style profile generated successfully for {course_code}.", "success")
    else:
        flash(result, "danger")

    return redirect(url_for("main.course_style_page"))


@main.route("/view-style-profile/<course_code>")
@login_required
def view_style_profile(course_code):
    course_code = course_code.upper()
    profile_path = os.path.join(
        current_app.config["PAST_PAPERS_FOLDER"],
        course_code,
        "style_profile.txt"
    )

    if not os.path.exists(profile_path):
        flash("Style profile file not found.", "warning")
        return redirect(url_for("main.course_style_page"))

    with open(profile_path, "r", encoding="utf-8") as f:
        profile_text = f.read()

    return render_template(
        "style_profile_view.html",
        course_code=course_code,
        profile_text=profile_text
    )
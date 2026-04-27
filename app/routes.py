import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, session, Response
from flask_login import login_required, current_user

from app import db
from app.models import Material, Question, Choice, QuizAttempt, QuizAnswer
from app.services.ai_service import generate_mcqs_from_text, clean_extracted_text_with_ai
from app.services.course_profile_service import build_style_profile_for_course
from app.services.lecture_file_service import extract_text_from_file, combine_extracted_text

main = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "html"}
VALID_DIFFICULTIES = {"Hot", "Moderate", "Cold", "All"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_material_or_404(material_id):
    return Material.query.filter_by(
        id=material_id,
        user_id=current_user.id
    ).first_or_404()


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

    return [question_map[qid] for qid in question_ids if qid in question_map]


def safe_question_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 5

    if count < 3:
        return 3

    if count > 20:
        return 20

    return count


def save_quiz_attempt(material, level, score, total_questions, results, attempt_type="normal"):
    attempt = QuizAttempt(
        user_id=current_user.id,
        material_id=material.id,
        level=level,
        score=score,
        total_questions=total_questions,
        attempt_type=attempt_type
    )

    db.session.add(attempt)
    db.session.flush()

    for item in results:
        answer = QuizAnswer(
            attempt_id=attempt.id,
            question_id=item["question"].id,
            selected_choice_id=item["selected_choice"].id if item["selected_choice"] else None,
            correct_choice_id=item["correct_choice"].id if item["correct_choice"] else None,
            is_correct=item["is_correct"]
        )
        db.session.add(answer)

    db.session.commit()
    return attempt


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/dashboard")
@login_required
def dashboard():
    materials = (
        Material.query
        .filter_by(user_id=current_user.id)
        .order_by(Material.is_pinned.desc(), Material.id.desc())
        .all()
    )

    total_materials = len(materials)

    total_questions = (
        Question.query
        .join(Material)
        .filter(Material.user_id == current_user.id)
        .count()
    )

    return render_template(
        "dashboard.html",
        user=current_user,
        materials=materials,
        total_materials=total_materials,
        total_questions=total_questions
    )


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
            user_id=current_user.id,
            course_code=course_code,
            title=title,
            filename=combined_filename_text,
            extracted_text=combined_text,
            cleaned_text=combined_text,
            quiz_difficulty="All",
            question_count=5,
            question_style="MCQ"
        )

        db.session.add(new_material)
        db.session.commit()

        flash("Lecture files uploaded and extracted successfully. Please review the extracted text before generating quiz.", "success")
        return redirect(url_for("main.review_material", material_id=new_material.id))

    return render_template("upload.html")


@main.route("/material/<int:material_id>")
@login_required
def view_material(material_id):
    material = get_user_material_or_404(material_id)

    question_count = Question.query.filter_by(material_id=material.id).count()

    hot_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Hot"
    ).count()

    moderate_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Moderate"
    ).count()

    cold_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Cold"
    ).count()

    recent_attempts = (
        QuizAttempt.query
        .filter_by(user_id=current_user.id, material_id=material.id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "material_detail.html",
        material=material,
        question_count=question_count,
        hot_count=hot_count,
        moderate_count=moderate_count,
        cold_count=cold_count,
        recent_attempts=recent_attempts
    )

@main.route("/material/<int:material_id>/questions")
@login_required
def question_bank(material_id):
    material = get_user_material_or_404(material_id)

    questions = (
        Question.query
        .filter_by(material_id=material.id)
        .order_by(Question.id.asc())
        .all()
    )

    if not questions:
        flash("No generated questions found yet. Generate a quiz first.", "warning")
        return redirect(url_for("main.view_material", material_id=material.id))

    hot_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Hot"
    ).count()

    moderate_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Moderate"
    ).count()

    cold_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Cold"
    ).count()

    return render_template(
        "question_bank.html",
        material=material,
        questions=questions,
        hot_count=hot_count,
        moderate_count=moderate_count,
        cold_count=cold_count
    )

@main.route("/material/<int:material_id>/questions/export")
@login_required
def export_question_bank(material_id):
    material = get_user_material_or_404(material_id)

    questions = (
        Question.query
        .filter_by(material_id=material.id)
        .order_by(Question.id.asc())
        .all()
    )

    if not questions:
        flash("No generated questions available to export.", "warning")
        return redirect(url_for("main.view_material", material_id=material.id))

    lines = []

    lines.append("TAPA Generated Question Bank")
    lines.append("=" * 32)
    lines.append(f"Material Title: {material.title}")
    lines.append(f"Course Code: {material.course_code or '-'}")
    lines.append(f"Source File(s): {material.filename}")
    lines.append(f"Total Questions: {len(questions)}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("")

    for index, question in enumerate(questions, start=1):
        lines.append(f"Question {index}")
        lines.append(f"Difficulty: {question.difficulty}")
        lines.append("")
        lines.append(question.question_text)
        lines.append("")

        choices = question.choices

        for choice_index, choice in enumerate(choices):
            letter = chr(65 + choice_index)
            marker = " [Correct]" if choice.is_correct else ""
            lines.append(f"{letter}. {choice.choice_text}{marker}")

        correct_choice = next((choice for choice in choices if choice.is_correct), None)

        lines.append("")

        if correct_choice:
            correct_letter = chr(65 + choices.index(correct_choice))
            lines.append(f"Correct Answer: {correct_letter}. {correct_choice.choice_text}")
        else:
            lines.append("Correct Answer: N/A")

        if question.hint:
            lines.append("")
            lines.append(f"Hint: {question.hint}")

        if question.explanation:
            lines.append("")
            lines.append(f"Explanation: {question.explanation}")

        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    export_text = "\n".join(lines)

    safe_title = secure_filename(material.title or "question_bank")
    filename = f"{safe_title}_question_bank.txt"

    return Response(
        export_text,
        mimetype="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@main.route("/material/<int:material_id>/review", methods=["GET", "POST"])
@login_required
def review_material(material_id):
    material = get_user_material_or_404(material_id)

    if request.method == "POST":
        cleaned_text = request.form.get("cleaned_text", "").strip()
        quiz_difficulty = request.form.get("quiz_difficulty", "All").strip()
        question_style = request.form.get("question_style", "MCQ").strip()
        quiz_focus = request.form.get("quiz_focus", "").strip()
        question_count = safe_question_count(request.form.get("question_count", 5))
        action = request.form.get("action", "save")

        if not cleaned_text:
            flash("Cleaned extracted text cannot be empty.", "danger")
            return redirect(url_for("main.review_material", material_id=material.id))

        if quiz_difficulty not in VALID_DIFFICULTIES:
            quiz_difficulty = "All"

        material.cleaned_text = cleaned_text
        material.quiz_difficulty = quiz_difficulty
        material.question_count = question_count
        material.question_style = question_style or "MCQ"
        material.quiz_focus = quiz_focus or None

        db.session.commit()

        if action == "generate":
            existing_question_count = Question.query.filter_by(
                material_id=material.id
            ).count()

            if existing_question_count > 0:
                return redirect(url_for(
                    "main.regenerate_confirm",
                    material_id=material.id
                ))

            return redirect(url_for(
                "main.generate_first_quiz",
                material_id=material.id
            ))

        flash("Material review and quiz preferences saved.", "success")
        return redirect(url_for("main.view_material", material_id=material.id))

    if not material.cleaned_text:
        material.cleaned_text = material.extracted_text
        db.session.commit()

    return render_template("material_review.html", material=material)

@main.route("/material/<int:material_id>/clean-text", methods=["POST"])
@login_required
def clean_material_text(material_id):
    material = get_user_material_or_404(material_id)

    current_text = request.form.get("cleaned_text", "").strip()

    if not current_text:
        current_text = material.cleaned_text or material.extracted_text or ""

    if not current_text.strip():
        flash("There is no extracted text to clean.", "warning")
        return redirect(url_for("main.review_material", material_id=material.id))

    gemini_api_key = current_app.config.get("GEMINI_API_KEY")

    if not gemini_api_key:
        flash("Gemini API key is missing.", "danger")
        return redirect(url_for("main.review_material", material_id=material.id))

    cleaned_text = clean_extracted_text_with_ai(
        current_text,
        gemini_api_key
    )

    if not cleaned_text:
        flash("AI text cleaning failed. Please try again or edit the text manually.", "danger")
        return redirect(url_for("main.review_material", material_id=material.id))

    material.cleaned_text = cleaned_text
    db.session.commit()

    flash("Extracted text cleaned successfully using AI.", "success")
    return redirect(url_for("main.review_material", material_id=material.id))

@main.route("/material/<int:material_id>/regenerate-confirm")
@login_required
def regenerate_confirm(material_id):
    material = get_user_material_or_404(material_id)

    question_count = Question.query.filter_by(material_id=material.id).count()

    if question_count == 0:
        return redirect(url_for("main.generate_first_quiz", material_id=material.id))

    attempt_count = (
        QuizAttempt.query
        .filter_by(user_id=current_user.id, material_id=material.id)
        .count()
    )

    return render_template(
        "regenerate_confirm.html",
        material=material,
        question_count=question_count,
        attempt_count=attempt_count
    )

@main.route("/generate-first-quiz/<int:material_id>")
@login_required
def generate_first_quiz(material_id):
    material = get_user_material_or_404(material_id)

    question_count = Question.query.filter_by(material_id=material.id).count()

    if question_count > 0:
        return redirect(url_for("main.regenerate_confirm", material_id=material.id))

    return render_template("generate_first_quiz.html", material=material)

@main.route("/generate-quiz/<int:material_id>", methods=["POST"])
@login_required
def generate_quiz(material_id):
    material = get_user_material_or_404(material_id)

    existing_question_count = Question.query.filter_by(material_id=material.id).count()
    confirm_regenerate = request.form.get("confirm_regenerate") == "yes"

    if existing_question_count > 0 and not confirm_regenerate:
        return redirect(url_for("main.regenerate_confirm", material_id=material.id))

    source_text = material.cleaned_text or material.extracted_text

    if not source_text:
        flash("This material has no text to generate questions from.", "warning")
        return redirect(url_for("main.review_material", material_id=material.id))

    gemini_api_key = current_app.config.get("GEMINI_API_KEY")

    if not gemini_api_key:
        flash("Gemini API key is missing.", "danger")
        return redirect(url_for("main.review_material", material_id=material.id))

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
        source_text,
        gemini_api_key,
        course_code=material.course_code,
        style_profile_text=style_profile_text,
        question_count=material.question_count or 5,
        quiz_difficulty=material.quiz_difficulty or "All",
        question_style=material.question_style or "MCQ",
        quiz_focus=material.quiz_focus
    )

    if not generated_questions:
        flash("Failed to generate quiz questions.", "danger")
        return redirect(url_for("main.review_material", material_id=material.id))

    for q in generated_questions:
        new_question = Question(
            material_id=material.id,
            question_text=q["question_text"],
            difficulty=q["difficulty"],
            question_type=q.get("question_type", "mcq"),
            hint=q.get("hint", ""),
            explanation=q.get("explanation", "")
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
    material = get_user_material_or_404(material_id)
    questions = Question.query.filter_by(material_id=material.id).all()

    if not questions:
        flash("No quiz questions generated yet.", "warning")
        return redirect(url_for("main.review_material", material_id=material.id))

    hot_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Hot"
    ).count()

    moderate_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Moderate"
    ).count()

    cold_count = Question.query.filter_by(
        material_id=material.id,
        difficulty="Cold"
    ).count()

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
    material = get_user_material_or_404(material_id)

    if level not in VALID_DIFFICULTIES:
        flash("Invalid difficulty level.", "danger")
        return redirect(url_for("main.choose_level", material_id=material.id))

    questions = get_filtered_questions(material.id, level)

    if not questions:
        flash(f"No {level} questions available for this quiz.", "warning")
        return redirect(url_for("main.choose_level", material_id=material.id))

    session[f"quiz_{material_id}_{level}_answers"] = {}
    session.pop(f"retry_{material_id}_{level}_question_ids", None)
    session.pop(f"retry_{material_id}_{level}_answers", None)

    return redirect(url_for(
        "main.quiz_question",
        material_id=material.id,
        level=level,
        question_number=1
    ))


@main.route("/quiz/<int:material_id>/<level>/<int:question_number>", methods=["GET", "POST"])
@login_required
def quiz_question(material_id, level, question_number):
    material = get_user_material_or_404(material_id)

    if level not in VALID_DIFFICULTIES:
        flash("Invalid difficulty level.", "danger")
        return redirect(url_for("main.choose_level", material_id=material.id))

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

    selected_answer = answers.get(str(current_question.id))
    feedback_mode = False
    feedback_correct = False

    correct_choice = Choice.query.filter_by(
        question_id=current_question.id,
        is_correct=True
    ).first()

    if request.method == "POST":
        action = request.form.get("action", "check")

        if action == "check":
            selected_choice_id = request.form.get("selected_choice")

            if not selected_choice_id:
                flash("Please select an answer before checking.", "warning")
                return redirect(url_for(
                    "main.quiz_question",
                    material_id=material.id,
                    level=level,
                    question_number=question_number
                ))

            answers[str(current_question.id)] = int(selected_choice_id)
            session[session_key] = answers

            selected_answer = int(selected_choice_id)
            feedback_mode = True
            feedback_correct = correct_choice is not None and selected_answer == correct_choice.id

        elif action == "continue":
            next_question_number = question_number + 1

            if next_question_number > total_questions:
                return redirect(url_for(
                    "main.quiz_result",
                    material_id=material.id,
                    level=level
                ))

            return redirect(url_for(
                "main.quiz_question",
                material_id=material.id,
                level=level,
                question_number=next_question_number
            ))

    return render_template(
        "quiz_question.html",
        material=material,
        question=current_question,
        question_number=question_number,
        total_questions=total_questions,
        selected_answer=selected_answer,
        level=level,
        feedback_mode=feedback_mode,
        feedback_correct=feedback_correct,
        correct_choice=correct_choice
    )


@main.route("/quiz-result/<int:material_id>/<level>")
@login_required
def quiz_result(material_id, level):
    material = get_user_material_or_404(material_id)

    if level not in VALID_DIFFICULTIES:
        flash("Invalid difficulty level.", "danger")
        return redirect(url_for("main.choose_level", material_id=material.id))

    questions = get_filtered_questions(material.id, level)

    session_key = f"quiz_{material_id}_{level}_answers"
    answers = session.get(session_key, {})

    score = 0
    results = []
    wrong_question_ids = []

    for question in questions:
        correct_choice = Choice.query.filter_by(
            question_id=question.id,
            is_correct=True
        ).first()

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

    attempt = save_quiz_attempt(
        material=material,
        level=level,
        score=score,
        total_questions=total_questions,
        results=results,
        attempt_type="normal"
    )

    return render_template(
        "quiz_result.html",
        material=material,
        score=score,
        total_questions=total_questions,
        results=results,
        level=level,
        retry_available=retry_available,
        attempt=attempt
    )


@main.route("/retry-wrong/<int:material_id>/<level>")
@login_required
def retry_wrong(material_id, level):
    material = get_user_material_or_404(material_id)

    if level not in VALID_DIFFICULTIES:
        flash("Invalid difficulty level.", "danger")
        return redirect(url_for("main.choose_level", material_id=material.id))

    questions = get_retry_questions(material.id, level)

    if not questions:
        flash("No wrong questions available to retry.", "warning")
        return redirect(url_for(
            "main.quiz_result",
            material_id=material.id,
            level=level
        ))

    session[f"retry_{material_id}_{level}_answers"] = {}

    return redirect(url_for(
        "main.retry_question",
        material_id=material.id,
        level=level,
        question_number=1
    ))


@main.route("/retry-quiz/<int:material_id>/<level>/<int:question_number>", methods=["GET", "POST"])
@login_required
def retry_question(material_id, level, question_number):
    material = get_user_material_or_404(material_id)

    if level not in VALID_DIFFICULTIES:
        flash("Invalid difficulty level.", "danger")
        return redirect(url_for("main.choose_level", material_id=material.id))

    questions = get_retry_questions(material.id, level)

    if not questions:
        flash("No retry questions found.", "warning")
        return redirect(url_for("main.dashboard"))

    total_questions = len(questions)

    if question_number < 1 or question_number > total_questions:
        return redirect(url_for(
            "main.retry_result",
            material_id=material.id,
            level=level
        ))

    current_question = questions[question_number - 1]
    session_key = f"retry_{material_id}_{level}_answers"
    answers = session.get(session_key, {})

    selected_answer = answers.get(str(current_question.id))
    feedback_mode = False
    feedback_correct = False

    correct_choice = Choice.query.filter_by(
        question_id=current_question.id,
        is_correct=True
    ).first()

    if request.method == "POST":
        action = request.form.get("action", "check")

        if action == "check":
            selected_choice_id = request.form.get("selected_choice")

            if not selected_choice_id:
                flash("Please select an answer before checking.", "warning")
                return redirect(url_for(
                    "main.retry_question",
                    material_id=material.id,
                    level=level,
                    question_number=question_number
                ))

            answers[str(current_question.id)] = int(selected_choice_id)
            session[session_key] = answers

            selected_answer = int(selected_choice_id)
            feedback_mode = True
            feedback_correct = correct_choice is not None and selected_answer == correct_choice.id

        elif action == "continue":
            next_question_number = question_number + 1

            if next_question_number > total_questions:
                return redirect(url_for(
                    "main.retry_result",
                    material_id=material.id,
                    level=level
                ))

            return redirect(url_for(
                "main.retry_question",
                material_id=material.id,
                level=level,
                question_number=next_question_number
            ))

    return render_template(
        "quiz_question.html",
        material=material,
        question=current_question,
        question_number=question_number,
        total_questions=total_questions,
        selected_answer=selected_answer,
        level=f"{level} Retry",
        feedback_mode=feedback_mode,
        feedback_correct=feedback_correct,
        correct_choice=correct_choice
    )


@main.route("/retry-result/<int:material_id>/<level>")
@login_required
def retry_result(material_id, level):
    material = get_user_material_or_404(material_id)

    if level not in VALID_DIFFICULTIES:
        flash("Invalid difficulty level.", "danger")
        return redirect(url_for("main.choose_level", material_id=material.id))

    questions = get_retry_questions(material.id, level)

    session_key = f"retry_{material_id}_{level}_answers"
    answers = session.get(session_key, {})

    score = 0
    results = []

    for question in questions:
        correct_choice = Choice.query.filter_by(
            question_id=question.id,
            is_correct=True
        ).first()

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

    attempt = save_quiz_attempt(
        material=material,
        level=level,
        score=score,
        total_questions=total_questions,
        results=results,
        attempt_type="retry"
    )

    return render_template(
        "quiz_result.html",
        material=material,
        score=score,
        total_questions=total_questions,
        results=results,
        level=f"{level} Retry",
        retry_available=False,
        attempt=attempt
    )


@main.route("/history")
@login_required
def history():
    attempts = (
        QuizAttempt.query
        .filter_by(user_id=current_user.id)
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    return render_template("history.html", attempts=attempts)

@main.route("/material/<int:material_id>/attempts")
@login_required
def material_attempts(material_id):
    material = get_user_material_or_404(material_id)

    attempts = (
        QuizAttempt.query
        .filter_by(user_id=current_user.id, material_id=material.id)
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    total_attempts = len(attempts)

    best_attempt = None
    if attempts:
        best_attempt = max(
            attempts,
            key=lambda attempt: (
                attempt.score / attempt.total_questions
                if attempt.total_questions > 0 else 0
            )
        )

    normal_count = sum(1 for attempt in attempts if attempt.attempt_type == "normal")
    retry_count = sum(1 for attempt in attempts if attempt.attempt_type == "retry")

    return render_template(
        "material_attempts.html",
        material=material,
        attempts=attempts,
        total_attempts=total_attempts,
        best_attempt=best_attempt,
        normal_count=normal_count,
        retry_count=retry_count
    )


@main.route("/attempt/<int:attempt_id>")
@login_required
def attempt_detail(attempt_id):
    attempt = (
        QuizAttempt.query
        .filter_by(id=attempt_id, user_id=current_user.id)
        .first_or_404()
    )

    answers = (
        QuizAnswer.query
        .filter_by(attempt_id=attempt.id)
        .join(Question)
        .order_by(Question.id.asc())
        .all()
    )

    return render_template(
        "attempt_detail.html",
        attempt=attempt,
        answers=answers
    )

@main.route("/material/<int:material_id>/toggle-pin", methods=["POST"])
@login_required
def toggle_pin_material(material_id):
    material = get_user_material_or_404(material_id)

    material.is_pinned = not material.is_pinned
    db.session.commit()

    if material.is_pinned:
        flash("Material pinned to your dashboard.", "success")
    else:
        flash("Material unpinned from your dashboard.", "success")

    next_url = request.form.get("next") or url_for("main.dashboard")
    return redirect(next_url)

@main.route("/material/<int:material_id>/delete", methods=["POST"])
@login_required
def delete_material(material_id):
    material = get_user_material_or_404(material_id)

    material_title = material.title

    db.session.delete(material)
    db.session.commit()

    flash(f"Material '{material_title}' has been deleted successfully.", "success")
    return redirect(url_for("main.dashboard"))


@main.route("/attempt/<int:attempt_id>/delete", methods=["POST"])
@login_required
def delete_attempt(attempt_id):
    attempt = (
        QuizAttempt.query
        .filter_by(id=attempt_id, user_id=current_user.id)
        .first_or_404()
    )

    db.session.delete(attempt)
    db.session.commit()

    flash("Quiz attempt has been deleted successfully.", "success")
    return redirect(url_for("main.history"))


@main.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", "").strip() or None
        current_user.student_id = request.form.get("student_id", "").strip() or None
        current_user.programme = request.form.get("programme", "").strip() or None
        current_user.faculty = request.form.get("faculty", "").strip() or None
        current_user.year_of_study = request.form.get("year_of_study", "").strip() or None

        db.session.commit()

        flash("Student profile updated successfully.", "success")
        return redirect(url_for("main.profile"))

    materials = (
        Material.query
        .filter_by(user_id=current_user.id)
        .order_by(Material.id.desc())
        .all()
    )

    total_materials = len(materials)

    total_questions = (
        Question.query
        .join(Material)
        .filter(Material.user_id == current_user.id)
        .count()
    )

    total_attempts = (
        QuizAttempt.query
        .filter_by(user_id=current_user.id)
        .count()
    )

    recent_materials = materials[:5]

    recent_attempts = (
        QuizAttempt.query
        .filter_by(user_id=current_user.id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "profile.html",
        user=current_user,
        total_materials=total_materials,
        total_questions=total_questions,
        total_attempts=total_attempts,
        recent_materials=recent_materials,
        recent_attempts=recent_attempts
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

    success, result = build_style_profile_for_course(
        course_code,
        base_path,
        gemini_api_key
    )

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
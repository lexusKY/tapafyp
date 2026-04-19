import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
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

        if not title:
            flash("Please enter a title.", "danger")
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

    old_questions = Question.query.filter_by(material_id=material.id).all()

    for question in old_questions:
        Choice.query.filter_by(question_id=question.id).delete()

    Question.query.filter_by(material_id=material.id).delete()
    db.session.commit()

    generated_questions = generate_mcqs_from_text(material.extracted_text, gemini_api_key)

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
    return redirect(url_for("main.quiz", material_id=material.id))


@main.route("/quiz/<int:material_id>")
@login_required
def quiz(material_id):
    material = Material.query.get_or_404(material_id)
    questions = Question.query.filter_by(material_id=material.id).all()
    return render_template("quiz.html", material=material, questions=questions)


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
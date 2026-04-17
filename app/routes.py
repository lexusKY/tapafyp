import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import Material, Question, Choice
from app.services.pdf_service import extract_text_from_pdf
from app.services.ai_service import extract_text_with_gemini, generate_mcqs_from_text

main = Blueprint("main", __name__)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "pdf"


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
        if "pdf_file" not in request.files:
            flash("No file part found.", "danger")
            return redirect(url_for("main.upload"))

        file = request.files["pdf_file"]

        if file.filename == "":
            flash("Please choose a PDF file.", "danger")
            return redirect(url_for("main.upload"))

        title = request.form.get("title", "").strip()

        if not title:
            flash("Please enter a title.", "danger")
            return redirect(url_for("main.upload"))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            upload_folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            extracted_text = extract_text_from_pdf(file_path)
            extraction_method = "PyMuPDF"

            if not extracted_text:
                gemini_api_key = current_app.config.get("GEMINI_API_KEY")
                if gemini_api_key:
                    extracted_text = extract_text_with_gemini(file_path, gemini_api_key)
                    extraction_method = "Gemini"
                else:
                    extraction_method = "None"

            new_material = Material(
                title=title,
                filename=filename,
                extracted_text=extracted_text
            )

            db.session.add(new_material)
            db.session.commit()

            if extracted_text:
                flash(f"PDF uploaded successfully. Text extracted using {extraction_method}.", "success")
            else:
                flash("PDF uploaded, but text extraction failed. Check your Gemini API key or try another file.", "warning")

            return redirect(url_for("main.dashboard"))

        flash("Only PDF files are allowed.", "danger")
        return redirect(url_for("main.upload"))

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
import os

from app.services.pdf_service import extract_text_from_pdf
from app.services.ai_service import extract_text_with_gemini, generate_style_profile


def build_style_profile_for_course(course_code, base_path, gemini_api_key):
    course_folder = os.path.join(base_path, course_code, "main_reference")

    if not os.path.exists(course_folder):
        return False, f"Course folder not found: {course_folder}"

    pdf_files = [f for f in os.listdir(course_folder) if f.lower().endswith(".pdf")]

    if not pdf_files:
        return False, "No PDF files found in main_reference."

    combined_text_parts = []

    for filename in sorted(pdf_files, reverse=True):
        pdf_path = os.path.join(course_folder, filename)

        extracted_text = extract_text_from_pdf(pdf_path)

        if not extracted_text and gemini_api_key:
            extracted_text = extract_text_with_gemini(pdf_path, gemini_api_key)

        if extracted_text:
            combined_text_parts.append(f"\n===== FILE: {filename} =====\n")
            combined_text_parts.append(extracted_text)
        else:
            combined_text_parts.append(f"\n===== FILE: {filename} =====\n")
            combined_text_parts.append("Text extraction failed for this file.\n")

    combined_exam_text = "\n".join(combined_text_parts).strip()

    if not combined_exam_text:
        return False, "Failed to extract any usable text from the reference papers."

    style_profile_text = generate_style_profile(course_code, combined_exam_text, gemini_api_key)

    if not style_profile_text:
        return False, "Failed to generate style profile with Gemini."

    output_path = os.path.join(base_path, course_code, "style_profile.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(style_profile_text)

    return True, output_path
import os

from app.services.pdf_service import extract_text_from_pdf
from app.services.ai_service import extract_text_with_gemini
from app.services.docx_service import extract_text_from_docx
from app.services.pptx_service import extract_text_from_pptx
from app.services.html_service import extract_text_from_html


def extract_text_from_file(file_path, extension, gemini_api_key=None):
    extension = extension.lower()

    if extension == "pdf":
        extracted_text = extract_text_from_pdf(file_path)

        if not extracted_text and gemini_api_key:
            extracted_text = extract_text_with_gemini(file_path, gemini_api_key)

        return extracted_text

    if extension == "docx":
        return extract_text_from_docx(file_path)

    if extension == "pptx":
        return extract_text_from_pptx(file_path)

    if extension == "html":
        return extract_text_from_html(file_path)

    return None


def combine_extracted_text(file_results):
    combined_parts = []

    for item in file_results:
        combined_parts.append(f"===== FILE: {item['filename']} =====")
        if item["text"]:
            combined_parts.append(item["text"])
        else:
            combined_parts.append("Text extraction failed.")
        combined_parts.append("")

    return "\n".join(combined_parts).strip()
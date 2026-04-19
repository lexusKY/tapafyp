from docx import Document


def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        extracted_text = "\n".join(paragraphs).strip()

        if not extracted_text:
            return None

        return extracted_text

    except Exception as e:
        print(f"DOCX extraction error: {e}")
        return None
import fitz


def extract_text_from_pdf(pdf_path):
    extracted_text = ""

    try:
        doc = fitz.open(pdf_path)

        for page_number, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            print(f"Page {page_number} extracted characters: {len(page_text)}")
            extracted_text += page_text

        doc.close()

        extracted_text = extracted_text.strip()

        if not extracted_text:
            return None

        return extracted_text

    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None
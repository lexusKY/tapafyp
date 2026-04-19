from bs4 import BeautifulSoup


def extract_text_from_html(html_path):
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        extracted_text = soup.get_text(separator="\n")
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines).strip()

        if not cleaned_text:
            return None

        return cleaned_text

    except Exception as e:
        print(f"HTML extraction error: {e}")
        return None
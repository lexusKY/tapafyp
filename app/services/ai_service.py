from google import genai
from google.genai import types
import json


def extract_text_with_gemini(pdf_path, api_key):
    try:
        client = genai.Client(api_key=api_key)

        uploaded_file = client.files.upload(file=pdf_path)

        prompt = """
Read this uploaded exam paper carefully.

Your task:
1. Extract all readable text from the document.
2. Preserve the original structure as much as possible.
3. Include section headings, question numbers, and instructions.
4. Return only the extracted text.
5. Do not explain anything.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                uploaded_file,
                prompt
            ],
            config=types.GenerateContentConfig(
                temperature=0
            )
        )

        if response.text:
            return response.text.strip()

        return None

    except Exception as e:
        print(f"Gemini extraction error: {e}")
        return None


def generate_mcqs_from_text(extracted_text, api_key):
    try:
        client = genai.Client(api_key=api_key)

        shortened_text = extracted_text[:12000]

        prompt = f"""
You are helping build an educational quiz system.

Based on the exam text below, generate 5 original multiple-choice questions for student revision.

Rules:
1. Base the questions on the uploaded exam content.
2. Keep the questions clear and suitable for revision.
3. Each question must have exactly 4 answer choices.
4. Only 1 choice must be correct.
5. Include a difficulty level using only one of these values:
   - Hot
   - Moderate
   - Cold
6. Return valid JSON only.
7. Do not use markdown fences.
8. Do not add explanations before or after the JSON.

Return this exact JSON structure:
[
  {{
    "question_text": "string",
    "difficulty": "Hot",
    "choices": [
      {{"choice_text": "string", "is_correct": true}},
      {{"choice_text": "string", "is_correct": false}},
      {{"choice_text": "string", "is_correct": false}},
      {{"choice_text": "string", "is_correct": false}}
    ]
  }}
]

Exam text:
{shortened_text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3
            )
        )

        if not response.text:
            print("Gemini MCQ generation error: empty response")
            return None

        cleaned_text = response.text.strip()

        print("========== RAW GEMINI MCQ RESPONSE START ==========")
        print(cleaned_text)
        print("========== RAW GEMINI MCQ RESPONSE END ==========")

        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text.replace("```json", "", 1).strip()

        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.replace("```", "", 1).strip()

        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3].strip()

        questions = json.loads(cleaned_text)
        return questions

    except Exception as e:
        print(f"Gemini MCQ generation error: {e}")
        return None
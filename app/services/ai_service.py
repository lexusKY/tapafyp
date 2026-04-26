from google import genai
from google.genai import types
import json


def extract_text_with_gemini(pdf_path, api_key):
    try:
        client = genai.Client(api_key=api_key)

        uploaded_file = client.files.upload(file=pdf_path)

        prompt = """
Read this uploaded document carefully.

Your task:
1. Extract all readable text from the document.
2. Preserve the original structure as much as possible.
3. Preserve headings, question numbers, bullet points, tables, formulas, calculations, and examples.
4. If there is a table, convert it into a clear markdown-style table when possible.
5. If there are formulas or calculations, keep them on separate lines and avoid merging symbols incorrectly.
6. Return only the extracted text.
7. Do not explain anything.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded_file, prompt],
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


def generate_mcqs_from_text(
    extracted_text,
    api_key,
    course_code=None,
    style_profile_text=None,
    question_count=5,
    quiz_difficulty="All",
    question_style="MCQ",
    quiz_focus=None
):
    try:
        client = genai.Client(api_key=api_key)

        shortened_text = extracted_text[:18000]
        style_profile_text = (style_profile_text or "")[:12000]

        try:
            question_count = int(question_count)
        except ValueError:
            question_count = 5

        if question_count < 3:
            question_count = 3

        if question_count > 20:
            question_count = 20

        allowed_difficulties = ["Hot", "Moderate", "Cold"]

        if quiz_difficulty not in ["Hot", "Moderate", "Cold", "All"]:
            quiz_difficulty = "All"

        difficulty_instruction = (
            "Use a balanced mix of Hot, Moderate, and Cold difficulty."
            if quiz_difficulty == "All"
            else f"Generate questions using only {quiz_difficulty} difficulty."
        )

        prompt = f"""
You are helping build TAPA, an educational revision quiz system.

Generate {question_count} original multiple-choice questions based on the student's uploaded lecture notes.

Course code:
{course_code or "Unknown"}

Question style:
{question_style or "MCQ"}

Quiz difficulty preference:
{quiz_difficulty}

Difficulty instruction:
{difficulty_instruction}

Student quiz focus:
{quiz_focus if quiz_focus else "No specific focus provided."}

Course style profile:
{style_profile_text if style_profile_text else "No style profile provided."}

Reviewed lecture notes text:
{shortened_text}

Rules:
1. Base the questions on the reviewed lecture notes.
2. If a course style profile is provided, follow its tone, difficulty pattern, and question style.
3. If a quiz focus is provided, prioritize that focus while still using the lecture notes.
4. Do not copy past year exam questions exactly.
5. Make the questions suitable for student revision in UTAR-like style.
6. Each question must have exactly 4 choices.
7. Only 1 choice must be correct.
8. difficulty must use only: Hot, Moderate, Cold.
9. {difficulty_instruction}
10. question_type should be "mcq".
11. Include a short hint for the learner before answering.
12. Include a short explanation for why the correct answer is correct.
13. Return valid JSON only.
"""

        response_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "difficulty": {
                        "type": "string",
                        "enum": allowed_difficulties
                    },
                    "question_type": {"type": "string"},
                    "hint": {"type": "string"},
                    "explanation": {"type": "string"},
                    "choices": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "properties": {
                                "choice_text": {"type": "string"},
                                "is_correct": {"type": "boolean"}
                            },
                            "required": ["choice_text", "is_correct"]
                        }
                    }
                },
                "required": [
                    "question_text",
                    "difficulty",
                    "question_type",
                    "hint",
                    "explanation",
                    "choices"
                ]
            }
        }

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )

        if not response.text:
            print("Gemini MCQ generation error: empty response")
            return None

        questions = getattr(response, "parsed", None)
        if questions is None:
            questions = json.loads(response.text)

        if not isinstance(questions, list) or len(questions) == 0:
            print("Gemini MCQ generation error: parsed response is empty or invalid")
            return None

        validated_questions = []

        for q in questions:
            if "choices" not in q or len(q["choices"]) != 4:
                print("Gemini MCQ generation error: each question must have exactly 4 choices")
                return None

            correct_count = sum(1 for c in q["choices"] if c.get("is_correct") is True)
            if correct_count != 1:
                print("Gemini MCQ generation error: each question must have exactly 1 correct answer")
                return None

            if quiz_difficulty != "All":
                q["difficulty"] = quiz_difficulty

            validated_questions.append(q)

        return validated_questions

    except Exception as e:
        print(f"Gemini MCQ generation error: {e}")
        return None


def generate_style_profile(course_code, combined_exam_text, api_key):
    try:
        client = genai.Client(api_key=api_key)

        shortened_text = combined_exam_text[:30000]

        prompt = f"""
You are analyzing past year final exam papers for a university course.

Course code: {course_code}

Based on the exam papers below, create a style profile for this course.

Your output must be plain text only.
Do not use markdown code fences.
Do not output JSON.

Use this exact format:

Course Code: {course_code}

1. Common Exam Format
- ...
- ...
- ...

2. Common Question Types
- ...
- ...
- ...

3. Common Topics / Repeated Focus
- ...
- ...
- ...

4. Common Command Words
- ...
- ...
- ...

5. Answer Style Expected
- ...
- ...
- ...

6. Difficulty Pattern
- ...
- ...
- ...

7. Coding Question Pattern
- ...
- ...
- ...

8. UI / Practical Pattern
- ...
- ...
- ...

9. Notes for AI Question Generation
- ...
- ...
- ...

Exam papers text:
{shortened_text}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )

        if response.text:
            return response.text.strip()

        return None

    except Exception as e:
        print(f"Gemini style profile generation error: {e}")
        return None
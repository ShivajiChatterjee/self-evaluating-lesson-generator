from google.genai import types


def extract_response_text(response: types.GenerateContentResponse) -> str:
    if (
        not response.candidates
        or not response.candidates[0].content
        or not response.candidates[0].content.parts
    ):
        return ""

    text = ""
    for part in response.candidates[0].content.parts:
        if part.thought or not isinstance(part.text, str):
            continue
        if text and part.text and text[-1].isalnum() and part.text[0].isalnum():
            text += " "
        text += part.text

    return text

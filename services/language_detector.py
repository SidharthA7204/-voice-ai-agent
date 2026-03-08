from langdetect import detect

def detect_language(text: str):
    try:
        language = detect(text)
        return language
    except Exception as e:
        raise Exception(f"Language Detection Error: {str(e)}")
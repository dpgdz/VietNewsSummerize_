import re

def clean_text(text: str) -> str:
    """
    Xóa thừa whitespace, HTML tags, và normalize unicode.
    """
    # Loại bỏ HTML tags còn sót
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text
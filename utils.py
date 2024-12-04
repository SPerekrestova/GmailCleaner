import re

def contains_html(text):
    """Check if the text contains HTML tags."""
    return bool(re.search(r'<.*?>', text))
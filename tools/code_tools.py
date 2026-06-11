import re

def extract_code(text: str) -> tuple[str, str]:
    """Extract code and language from LLM response."""
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        language, code = matches[0]
        return language.lower().strip(), code.strip()
    
    return "python", text.strip()
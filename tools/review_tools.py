def extract_code_from_message(message: str) -> tuple[str, str]:
    """Extract code block and language from a user message."""
    import re
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, message, re.DOTALL)

    if matches:
        language, code = matches[0]
        return language.lower().strip() or "python", code.strip()

    # If no code block found, treat entire message as code
    return "python", message.strip()
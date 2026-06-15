from agent.prompts import SKILL_DETECTOR_PROMPT

def detect_skill(user_message: str , llm) -> str:
    """Detect which skill to  use based on user message"""
    prompt = SKILL_DETECTOR_PROMPT.format(message = user_message)
    response = llm.invoke([("human", prompt)])
    skill = response.content.strip().lower()

    valid_skills = ["code_execution", "code_review", "file_analysis", "general"]
    if skill not  in valid_skills:
        return "code_execution"
    
    return skill
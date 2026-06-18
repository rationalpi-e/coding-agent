from dotenv import load_dotenv
load_dotenv()

import os
from tools.file_tools import read_file, write_file, create_folder, list_files, delete_file
from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.prompts import (
    SYSTEM_PROMPT, TEST_WRITER_PROMPT, CODE_WRITER_PROMPT,
    FIXER_PROMPT, CODE_REVIEW_PROMPT, FILE_ANALYSIS_PROMPT
)
from executors.python_executor import run_python, run_python_with_tests
from executors.cpp_executor import run_cpp
from executors.sql_executor import run_sql
from tools.code_tools import extract_code
from tools.skill_detector import detect_skill
from tools.review_tools import extract_code_from_message
from memory.store import save_code, retrieve_similar_code, save_chat, retrieve_similar_chats


def get_llm(model_name: str):
    """Factory function — returns the right LLM based on selection."""
    if model_name == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in .env")
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)   

    elif model_name == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in .env")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    elif model_name == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-3-5-haiku-20241022", temperature=0)

    elif model_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)

    else:
        raise ValueError(f"Unknown model: {model_name}")


def get_user_message(state: AgentState) -> str:
    """Helper to extract the original user message from state."""
    for m in state["messages"]:
        if isinstance(m, tuple) and m[0] == "human":
            return m[1]
        
        elif hasattr(m, "type") and m.type == "human":
            return m.content
    return ""


def route_skill(state: AgentState) -> AgentState:
    """Detect which skill to use and route accordingly."""
    llm = state.get("llm")
    user_message = get_user_message(state)
    uploaded_file = state.get("uploaded_file_content", "")

    if uploaded_file:
        skill = "file_analysis"
    else:
        skill = detect_skill(user_message, llm)

    return {"skill": skill}


def write_tests(state: AgentState) -> AgentState:
    """Agent writes a failing test first."""
    llm = state.get("llm")
    user_message = get_user_message(state)
    language = state.get("language") or "python"

    if language != "python":
        return {"status": "writing_code", "test_code": ""}

    prompt = TEST_WRITER_PROMPT.format(problem=user_message)
    response = llm.invoke([("system", SYSTEM_PROMPT), ("human", prompt)])
    _, test_code = extract_code(response.content)

    return {
        "messages": [response],
        "test_code": test_code,
        "status": "writing_code"
    }


def write_code(state: AgentState) -> AgentState:
    """Agent writes code to pass the tests."""
    llm = state.get("llm")
    user_message = get_user_message(state)
    language = state.get("language") or "python"
    test_code = state.get("test_code", "")
    iteration = state.get("iteration_count", 0)

    past_solutions = retrieve_similar_code(user_message, language)
    memory_context = f"\n\nRelevant past solutions:\n{past_solutions}" if past_solutions else ""

    if test_code:
        prompt = CODE_WRITER_PROMPT.format(problem=user_message, tests=test_code)
    else:
        prompt = user_message

    response = llm.invoke([
        ("system", SYSTEM_PROMPT + memory_context),
        ("human", prompt)
    ])

    detected_language, code = extract_code(response.content)
    if detected_language and detected_language not in ("text", ""):
        language = detected_language

    return {
        "messages": [response],
        "code": code,
        "language": language,
        "iteration_count": iteration + 1,
        "status": "executing"
    }


def execute_code(state: AgentState) -> AgentState:
    """Run the code — with tests if available."""
    code = state.get("code", "")
    language = state.get("language", "python")
    test_code = state.get("test_code", "")

    if not code:
        return {"status": "done", "execution_result": "No code found"}

    if language == "python" and test_code:
        result = run_python_with_tests(code, test_code)
    elif language == "python":
        result = run_python(code)
    elif language in ("cpp", "c++"):
        result = run_cpp(code)
    elif language == "sql":
        result = run_sql(code)
    else:
        return {"status": "done", "execution_result": f"{language} executor coming soon"}

    output = result["stdout"] if result["stdout"] else result["stderr"]

    if result["success"]:
        return {"status": "done", "execution_result": output}
    else:
        return {
            "status": "fixing",
            "error": output,
            "execution_result": output
        }


def fix_code(state: AgentState) -> AgentState:
    """Agent reads the error and fixes the code."""
    llm = state.get("llm")
    user_message = get_user_message(state)
    error = state.get("error", "")
    code = state.get("code", "")
    test_code = state.get("test_code", "")
    iteration = state.get("iteration_count", 0)

    prompt = FIXER_PROMPT.format(
        error=error,
        problem=user_message,
        code=code,
        tests=test_code
    )

    response = llm.invoke([("system", SYSTEM_PROMPT), ("human", prompt)])
    _, fixed_code = extract_code(response.content)

    return {
        "messages": [response],
        "code": fixed_code,
        "iteration_count": iteration + 1,
        "status": "executing"
    }


def review_code(state: AgentState) -> AgentState:
    """Agent reviews code pasted by the user."""
    llm = state.get("llm")
    user_message = get_user_message(state)
    language, code = extract_code_from_message(user_message)

    prompt = CODE_REVIEW_PROMPT.format(code=code, language=language)
    response = llm.invoke([("system", SYSTEM_PROMPT), ("human", prompt)])

    return {
        "messages": [response],
        "status": "done",
        "execution_result": ""
    }


def analyze_file(state: AgentState) -> AgentState:
    """Agent analyzes an uploaded file."""
    llm = state.get("llm")
    user_message = get_user_message(state)
    file_content = state.get("uploaded_file_content", "")
    file_name = state.get("uploaded_file_name", "unknown")

    ext = file_name.split(".")[-1].lower() if "." in file_name else "python"
    language_map = {"py": "python", "cpp": "c++", "sql": "sql", "js": "javascript"}
    language = language_map.get(ext, ext)

    prompt = FILE_ANALYSIS_PROMPT.format(
        filename=file_name,
        language=language,
        content=file_content,
        task=user_message or "Analyze this file thoroughly"
    )

    response = llm.invoke([("system", SYSTEM_PROMPT), ("human", prompt)])

    return {
        "messages": [response],
        "status": "done",
        "execution_result": ""
    }


def handle_general(state: AgentState) -> AgentState:
    """Handle general coding questions."""
    llm = state.get("llm")
    user_message = get_user_message(state)
    response = llm.invoke([("system", SYSTEM_PROMPT), ("human", user_message)])
    return {
        "messages": [response],
        "status": "done",
        "execution_result": ""
    }


def save_to_memory(state: AgentState) -> AgentState:
    """Save successful solution to ChromaDB."""
    if state.get("status") == "done":
        user_message = get_user_message(state)
        code = state.get("code", "")
        language = state.get("language", "python")
        output = state.get("execution_result", "")
        agent_response = state["messages"][-1].content

        if code:
            save_code(user_message, code, language, output)
        save_chat(user_message, agent_response)

    return state


def should_continue(state: AgentState) -> str:
    if state.get("iteration_count", 0) >= 5:
        return "end"
    if state.get("status") == "done":
        return "end"
    if state.get("status") == "fixing":
        return "fix"
    return "end"


def route_to_skill(state: AgentState) -> str:
    skill = state.get("skill", "code_execution")
    if skill == "code_review":
        return "code_review"
    elif skill == "file_analysis":
        return "file_analysis"
    elif skill == "file_system":
        return "file_system"
    elif skill == "general":
        return "general"
    else:
        return "code_execution"
    
    
def handle_file_system(state: AgentState) -> AgentState:
    """Agent reads/writes files in the workspace."""
    from agent.prompts import FILE_SYSTEM_PROMPT
    llm = state.get("llm")
    user_message = get_user_message(state)

    # Get current workspace files for context
    files_result = list_files()
    current_files = files_result["files"] if files_result["success"] else []
    files_str = "\n".join(current_files) if current_files else "workspace is empty"

    prompt = FILE_SYSTEM_PROMPT.format(
        request=user_message,
        files=files_str
    )

    response = llm.invoke([("system", SYSTEM_PROMPT), ("human", prompt)])
    response_text = response.content

    # Parse and execute file operations from LLM response
    results = []
    lines = response_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("LIST"):
            files = list_files()
            results.append(f"📁 Workspace files:\n" + "\n".join(files["files"]) if files["files"] else "workspace is empty")

        elif line.startswith("CREATE_FOLDER "):
            folder = line.replace("CREATE_FOLDER ", "").strip()
            result = create_folder(folder)
            results.append(f"📁 Created folder: {result['path']}" if result["success"] else f"❌ {result['error']}")

        elif line.startswith("DELETE "):
            filename = line.replace("DELETE ", "").strip()
            result = delete_file(filename)
            results.append(f"🗑️ Deleted: {filename}" if result["success"] else f"❌ {result['error']}")

        elif line.startswith("READ "):
            filename = line.replace("READ ", "").strip()
            result = read_file(filename)
            if result["success"]:
                results.append(f"📄 {filename}:\n```\n{result['content']}\n```")
            else:
                results.append(f"❌ {result['error']}")

        elif line.startswith("WRITE "):
            filename = line.replace("WRITE ", "").strip()
            # Collect content until we hit ---END--- or next command
            content_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("---END---"):
                content_lines.append(lines[i])
                i += 1
            content = "\n".join(content_lines)
            result = write_file(filename, content)
            results.append(f"✅ Written: {result['path']}" if result["success"] else f"❌ {result['error']}")

        i += 1

    # If no commands were parsed, extract code blocks and save them
    if not results:
        import re
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, response_text, re.DOTALL)
        ext_map = {"python": "py", "cpp": "cpp", "sql": "sql", "javascript": "js"}

        for lang, code in matches:
            lang = lang.lower().strip() if lang else "python"
            ext = ext_map.get(lang, "txt")

            # Try to extract filename from response
            filename_match = re.search(r'(?:save|write|create|file)[^\n]*?([a-zA-Z0-9_/]+\.' + ext + r')', response_text, re.IGNORECASE)
            if filename_match:
                filename = filename_match.group(1)
            else:
                filename = f"output.{ext}"

            result = write_file(filename, code)
            results.append(f"✅ Saved to: {result['path']}" if result["success"] else f"❌ {result['error']}")

    ops_summary = "\n".join(results) if results else ""

    final_response = response_text
    if ops_summary:
        final_response += f"\n\n---\n**File operations:**\n{ops_summary}"

    return {
        "messages": [response],
        "status": "done",
        "execution_result": ops_summary
    }


# Build the graph
builder = StateGraph(AgentState)

builder.add_node("router", route_skill)
builder.add_node("write_tests", write_tests)
builder.add_node("write_code", write_code)
builder.add_node("executor", execute_code)
builder.add_node("fix_code", fix_code)
builder.add_node("code_review", review_code)
builder.add_node("file_analysis", analyze_file)
builder.add_node("file_system", handle_file_system)
builder.add_node("general", handle_general)
builder.add_node("memory", save_to_memory)

builder.set_entry_point("router")
builder.add_conditional_edges("router", route_to_skill, {
    "code_execution": "write_tests",
    "code_review": "code_review",
    "file_analysis": "file_analysis",
    "file_system": "file_system",
    "general": "general"
})
builder.add_edge("write_tests", "write_code")
builder.add_edge("write_code", "executor")
builder.add_conditional_edges("executor", should_continue, {
    "fix": "fix_code",
    "end": "memory"
})
builder.add_edge("fix_code", "executor")
builder.add_edge("code_review", "memory")
builder.add_edge("file_analysis", "memory")
builder.add_edge("file_system", "memory")
builder.add_edge("general", "memory")
builder.add_edge("memory", END)
graph = builder.compile()


def run_agent(
    user_message: str,
    language: str = "python",
    model_name: str = "groq",
    uploaded_file_content: str = "",
    uploaded_file_name: str = ""
) -> str:
    try:
        llm = get_llm(model_name)
    except ValueError as e:
        return f"⚠️ {str(e)} — please add the API key to your .env file"

    result = graph.invoke({
        "messages": [
            ("system", SYSTEM_PROMPT),
            ("human", user_message)
        ],
        "iteration_count": 0,
        "status": "writing",
        "language": language.lower(),
        "llm": llm,
        "uploaded_file_content": uploaded_file_content,
        "uploaded_file_name": uploaded_file_name
    })

    last_message = result["messages"][-1].content
    execution_result = result.get("execution_result", "")
    iterations = result.get("iteration_count", 0)
    test_code = result.get("test_code", "")
    skill = result.get("skill", "code_execution")

    response = last_message

    if skill == "code_execution":
        if test_code:
            response += f"\n\n---\n**Tests written:**\n```python\n{test_code}\n```"
        if execution_result:
            status = "✅ All tests passed" if result.get("status") == "done" else "❌ Tests failed"
            response += f"\n\n---\n**{status}** (iterations: {iterations})\n```\n{execution_result}\n```"

    return response

def run_agent_stream(
    user_message: str,
    language: str = "python",
    model_name: str = "groq",
    uploaded_file_content: str = "",
    uploaded_file_name: str = ""
):
    try:
        llm = get_llm(model_name)
    except ValueError as e:
        yield f"⚠️ {str(e)} — please add the API key to your .env file"
        return

    # Step 1 — detect skill
    from tools.skill_detector import detect_skill
    skill = detect_skill(user_message, llm)

    if uploaded_file_content:
        skill = "file_analysis"

    # Step 2 — for code execution, run the full graph (needs executors)
    if skill == "code_execution":
        result = graph.invoke({
            "messages": [("system", SYSTEM_PROMPT), ("human", user_message)],
            "iteration_count": 0,
            "status": "writing",
            "language": language.lower(),
            "llm": llm,
            "uploaded_file_content": uploaded_file_content,
            "uploaded_file_name": uploaded_file_name
        })

        last_message = result["messages"][-1].content
        execution_result = result.get("execution_result", "")
        iterations = result.get("iteration_count", 0)
        test_code = result.get("test_code", "")

        # Stream the final message
        for chunk in llm.stream([
            ("system", SYSTEM_PROMPT),
            ("human", f"Present this solution clearly:\n\n{last_message}")
        ]):
            if chunk.content:
                yield chunk.content

        if test_code:
            yield f"\n\n---\n**Tests written:**\n```python\n{test_code}\n```"
        if execution_result:
            status = "✅ All tests passed" if result.get("status") == "done" else "❌ Tests failed"
            yield f"\n\n---\n**{status}** (iterations: {iterations})\n```\n{execution_result}\n```"

    # Step 3 — for review, file analysis, general — stream directly, no graph needed
    elif skill == "code_review":
        from agent.prompts import CODE_REVIEW_PROMPT
        from tools.review_tools import extract_code_from_message
        lang, code = extract_code_from_message(user_message)
        prompt = CODE_REVIEW_PROMPT.format(code=code, language=lang)
        for chunk in llm.stream([("system", SYSTEM_PROMPT), ("human", prompt)]):
            if chunk.content:
                yield chunk.content

    elif skill == "file_analysis":
        from agent.prompts import FILE_ANALYSIS_PROMPT
        ext = uploaded_file_name.split(".")[-1].lower() if "." in uploaded_file_name else "python"
        language_map = {"py": "python", "cpp": "c++", "sql": "sql", "js": "javascript"}
        lang = language_map.get(ext, ext)
        prompt = FILE_ANALYSIS_PROMPT.format(
            filename=uploaded_file_name,
            language=lang,
            content=uploaded_file_content,
            task=user_message or "Analyze this file thoroughly"
        )
        for chunk in llm.stream([("system", SYSTEM_PROMPT), ("human", prompt)]):
            if chunk.content:
                yield chunk.content

    elif skill == "file_system":
        # Must run through graph so file operations actually execute
        result = graph.invoke({
            "messages": [("system", SYSTEM_PROMPT), ("human", user_message)],
            "iteration_count": 0,
            "status": "writing",
            "language": language.lower(),
            "llm": llm,
            "uploaded_file_content": uploaded_file_content,
            "uploaded_file_name": uploaded_file_name
        })

        last_message = result["messages"][-1].content
        execution_result = result.get("execution_result", "")

        # Stream the response
        for chunk in llm.stream([
            ("system", SYSTEM_PROMPT),
            ("human", f"Summarize what you did:\n\n{last_message}")
        ]):
            if chunk.content:
                yield chunk.content

        if execution_result:
            yield f"\n\n---\n**File operations:**\n{execution_result}"

            
    else:
        # General question — stream directly
        for chunk in llm.stream([("system", SYSTEM_PROMPT), ("human", user_message)]):
            if chunk.content:
                yield chunk.content
from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from executors.python_executor import run_python
from executors.cpp_executor import run_cpp
from executors.sql_executor import run_sql
from tools.code_tools import extract_code
from memory.store import save_code, retrieve_similar_code, save_chat, retrieve_similar_chats

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

def call_agent(state: AgentState) -> AgentState:
    messages = state["messages"]
    user_message = ""

    # Get the original user message
    for m in messages:
        if isinstance(m, tuple) and m[0] == "human":
            user_message = m[1]
            break
        elif hasattr(m, "type") and m.type == "human":
            user_message = m.content
            break

    language = state.get("language") or "python"

    # Retrieve similar past solutions from memory
    past_solutions = retrieve_similar_code(user_message, language)
    past_chats = retrieve_similar_chats(user_message)

    # Inject memory into system prompt if we have any
    memory_context = ""
    if past_solutions:
        memory_context += f"\n\nRelevant past solutions you wrote:\n{past_solutions}"
    if past_chats:
        memory_context += f"\n\nRelevant past conversations:\n{past_chats}"

    if memory_context:
        messages = [
            ("system", SYSTEM_PROMPT + memory_context),
            *[m for m in messages if not (isinstance(m, tuple) and m[0] == "system")]
        ]

    response = llm.invoke(messages)
    iteration = state.get("iteration_count", 0)
    extracted_language, code = extract_code(response.content)

    # Use language from UI selection if extractor returns generic result
    final_language = extracted_language if extracted_language != "python" else language

    return {
        "messages": [response],
        "iteration_count": iteration + 1,
        "code": code,
        "language": final_language,
        "status": "executing"
    }

def execute_code(state: AgentState) -> AgentState:
    code = state.get("code", "")
    language = state.get("language", "python")

    if not code:
        return {"status": "done", "execution_result": "No code found"}

    if language == "python":
        result = run_python(code)
    elif language in ("cpp", "c++"):
        result = run_cpp(code)
    elif language == "sql":
        result = run_sql(code)
    else:
        return {"status": "done", "execution_result": f"{language} executor coming soon"}

    output = result["stdout"] if result["success"] else result["stderr"]

    if result["success"]:
        return {"status": "done", "execution_result": output}
    else:
        return {
            "status": "fixing",
            "error": output,
            "execution_result": output,
            "messages": [(
                "human",
                f"Your code failed with this error:\n{output}\n\nFix the code and try again."
            )]
        }

def save_to_memory(state: AgentState) -> AgentState:
    """Save successful solution to ChromaDB."""
    if state.get("status") == "done":
        messages = state["messages"]
        user_message = ""
        for m in messages:
            if isinstance(m, tuple) and m[0] == "human":
                user_message = m[1]
                break
            elif hasattr(m, "type") and m.type == "human":
                user_message = m.content
                break

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

builder = StateGraph(AgentState)
builder.add_node("agent", call_agent)
builder.add_node("executor", execute_code)
builder.add_node("memory", save_to_memory)
builder.set_entry_point("agent")
builder.add_edge("agent", "executor")
builder.add_conditional_edges("executor", should_continue, {
    "fix": "agent",
    "end": "memory"
})
builder.add_edge("memory", END)

graph = builder.compile()

def run_agent(user_message: str) -> str:
    result = graph.invoke({
        "messages": [
            ("system", SYSTEM_PROMPT),
            ("human", user_message)
        ],
        "iteration_count": 0,
        "status": "writing"
    })

    last_message = result["messages"][-1].content
    execution_result = result.get("execution_result", "")

    if execution_result:
        return f"{last_message}\n\n---\n**Output:**\n```\n{execution_result}\n```"
    return last_message
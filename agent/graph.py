from dotenv import load_dotenv
from executors.sql_executor import run_sql
from executors.cpp_executor import run_cpp
load_dotenv()

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from executors.python_executor import run_python
from tools.code_tools import extract_code

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

def call_agent(state: AgentState) -> AgentState:
    messages = state["messages"]
    response = llm.invoke(messages)
    iteration = state.get("iteration_count", 0)
    language, code = extract_code(response.content)
    return {
        "messages": [response],
        "iteration_count": iteration + 1,
        "code": code,
        "language": language,
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
builder.set_entry_point("agent")
builder.add_edge("agent", "executor")
builder.add_conditional_edges("executor", should_continue, {
    "fix": "agent",
    "end": END
})

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
        return f"{last_message}\n\n---\n**Output:**\n```\n{execution_result}```"
    return last_message
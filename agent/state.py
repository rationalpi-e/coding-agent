from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]     #here messages has datatype of list but it can also have same as add_message
    code: Optional[str]
    language: Optional[str]
    test_code: Optional[str]
    execution_result: Optional[str]
    test_result: Optional[str]
    iteration_count: int
    status: Optional[str]
    error: Optional[str]
    llm: Optional[any]
    skill: Optional[str]
    upload_file_containt: Optional[str]
    upload_file_name: Optional[str]

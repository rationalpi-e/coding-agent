from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    '''This class contains everything that is included and passed around like the prompts, files , states,error, llm, response, skills etc.'''
    messages: Annotated[list, add_messages]     #here messages has type list and add_messages is metadata which langgraph uses to know how to change the list
    code: Optional[str]
    language: Optional[str]                 #python , c++ , sql
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

import chromadb
import hashlib

client = chromadb.PersistentClient(path="./chroma_db")

code_collection = client.get_or_create_collection("code_solutions")
chat_collection = client.get_or_create_collection("chat_history")

def save_code(problem: str , language: str , code: str , output: str):
    """save sussecful code solution to the memory"""
    doc_id = hashlib.md5(f"{problem}{language}".encode()).hexdigest()
    code_collection.upsert(
        ids = [doc_id],
        documents=[f"Problem: {problem}\n\nCode:\n{code}\n\nOutput:\n{output}"],
        metadatas=[{"language": language, "problem": problem}]
    )

def retrieve_similar_code(problem: str, language: str, n_results: int = 2) -> str:
    """Retrieve similar past solutions for context and this context goes to llm."""
    try:
        results = code_collection.query(
            query_texts=[problem],
            n_results=n_results,
            where={"language": language}
        )
        if results and results["documents"][0]:
            return "\n\n---\n".join(results["documents"][0])
        return ""
    except Exception:
        return ""
    
def save_chat(user_message: str, agent_response: str):
    """Save a conversation turn to memory."""
    doc_id = hashlib.md5(f"{user_message}".encode()).hexdigest()
    chat_collection.upsert(
        ids=[doc_id],
        documents=[f"User: {user_message}\n\nAgent: {agent_response}"],
        metadatas=[{"user_message": user_message}]
    )

def retrieve_similar_chats(user_message: str, n_results: int = 2) -> str:
    """Retrieve similar past conversations for context."""
    try:
        results = chat_collection.query(
            query_texts=[user_message],
            n_results=n_results
        )
        if results and results["documents"][0]:
            return "\n\n---\n".join(results["documents"][0])
        return ""
    except Exception:
        return ""
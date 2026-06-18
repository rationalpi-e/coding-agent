import os

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")

def _safe_path(filename: str) -> str:
    """Ensure the path stays inside workspace — no directory traversal."""
    safe = os.path.realpath(os.path.join(WORKSPACE_DIR, filename))
    if not safe.startswith(os.path.realpath(WORKSPACE_DIR)):
        raise ValueError(f"Access denied: {filename} is outside workspace")
    return safe

def read_file(filename: str) -> dict:
    """Read a file from workspace."""
    try:
        path = _safe_path(filename)
        if not os.path.exists(path):
            return {"success": False, "content": "", "error": f"{filename} does not exist"}
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "content": content, "error": ""}
    except Exception as e:
        return {"success": False, "content": "", "error": str(e)}

def write_file(filename: str, content: str) -> dict:
    """Write or overwrite a file in workspace."""
    try:
        path = _safe_path(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "error": "", "path": f"workspace/{filename}"}
    except Exception as e:
        return {"success": False, "error": str(e), "path": ""}

def create_folder(foldername: str) -> dict:
    """Create a folder inside workspace."""
    try:
        path = _safe_path(foldername)
        os.makedirs(path, exist_ok=True)
        return {"success": True, "error": "", "path": f"workspace/{foldername}"}
    except Exception as e:
        return {"success": False, "error": str(e), "path": ""}

def list_files(subfolder: str = "") -> dict:
    """List all files in workspace or a subfolder."""
    try:
        path = _safe_path(subfolder) if subfolder else WORKSPACE_DIR
        if not os.path.exists(path):
            return {"success": False, "files": [], "error": f"{subfolder} does not exist"}
        files = []
        for root, dirs, filenames in os.walk(path):
            # Skip hidden folders
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in filenames:
                if filename == ".gitkeep":
                    continue
                full_path = os.path.join(root, filename)
                relative = os.path.relpath(full_path, WORKSPACE_DIR)
                files.append(relative.replace("\\", "/"))
        return {"success": True, "files": files, "error": ""}
    except Exception as e:
        return {"success": False, "files": [], "error": str(e)}

def delete_file(filename: str) -> dict:
    """Delete a file from workspace."""
    try:
        path = _safe_path(filename)
        if not os.path.exists(path):
            return {"success": False, "error": f"{filename} does not exist"}
        os.remove(path)
        return {"success": True, "error": ""}
    except Exception as e:
        return {"success": False, "error": str(e)}
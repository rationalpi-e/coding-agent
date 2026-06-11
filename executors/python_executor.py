import subprocess
import tempfile
import os

def run_python(code: str) -> dict:
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        os.unlink(tmp_path)

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,    
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Timeout: code took too long", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

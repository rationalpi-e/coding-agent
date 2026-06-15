import subprocess
import tempfile
import os
import shutil
import sys

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


def run_python_with_tests(solution_code: str, test_code: str) -> dict:
    """Run pytest tests against a solution file."""
    tmp_dir = tempfile.mkdtemp()

    try:
        # Write solution.py
        solution_path = os.path.join(tmp_dir, "solution.py")
        with open(solution_path, "w") as f:
            f.write(solution_code)

        # Write test file
        test_path = os.path.join(tmp_dir, "test_solution.py")
        with open(test_path, "w") as f:
            f.write(test_code)

        # Run pytest
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_dir
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Timeout: tests took too long", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
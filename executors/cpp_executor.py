import subprocess
import tempfile
import os
import shutil

def run_cpp(code: str) -> dict:
    # Check if g++ is available
    if not shutil.which("g++"):
        return {
            "success": False,
            "stdout": "",
            "stderr": "g++ not found. Install MinGW on Windows: https://winlibs.com"
        }

    tmp_dir = tempfile.mkdtemp()
    src_path = os.path.join(tmp_dir, "main.cpp")
    out_path = os.path.join(tmp_dir, "main.exe")

    try:
        # Write the C++ source file
        with open(src_path, "w") as f:
            f.write(code)

        # Compile
        compile_result = subprocess.run(
            ["g++", src_path, "-o", out_path],
            capture_output=True,
            text=True,
            timeout=15
        )

        if compile_result.returncode != 0:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Compilation error:\n{compile_result.stderr}"
            }

        # Run the compiled binary
        run_result = subprocess.run(
            [out_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        return {
            "success": run_result.returncode == 0,
            "stdout": run_result.stdout,
            "stderr": run_result.stderr,
            "returncode": run_result.returncode
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Timeout: code took too long to compile or run"
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e)
        }
    finally:
        # Clean up temp files
        shutil.rmtree(tmp_dir, ignore_errors=True)
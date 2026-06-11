import sqlalchemy
from sqlalchemy import text

# Creates a local SQLite database file in your project
DATABASE_URL = "sqlite:///coding_agent.db"
engine = sqlalchemy.create_engine(DATABASE_URL)

def run_sql(code: str) -> dict:
    try:
        with engine.connect() as conn:
            # Handle multiple statements separated by semicolons
            statements = [s.strip() for s in code.split(";") if s.strip()]
            
            output = []
            for statement in statements:
                result = conn.execute(text(statement))
                conn.commit()
                
                # If it's a SELECT, fetch and format results
                if statement.strip().upper().startswith("SELECT"):
                    rows = result.fetchall()
                    cols = list(result.keys())
                    output.append(" | ".join(cols))
                    output.append("-" * 40)
                    for row in rows:
                        output.append(" | ".join(str(v) for v in row))
                else:
                    output.append(f"OK: {statement[:50]}...")

            return {
                "success": True,
                "stdout": "\n".join(output),
                "stderr": ""
            }

    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e)
        }
from app import create_app, db
from sqlalchemy import text

app = create_app()

def add_columns():
    """
    Manually adds the missing label columns to the 'brd' table.
    """
    new_columns = [
        ("executive_summary_label", "VARCHAR(100) DEFAULT 'Executive Summary'"),
        ("project_objectives_label", "VARCHAR(100) DEFAULT 'Project Objectives'"),
        ("project_scope_label", "VARCHAR(100) DEFAULT 'Project Scope'"),
        ("business_requirements_label", "VARCHAR(100) DEFAULT 'Business Requirements'"),
        ("key_stakeholders_label", "VARCHAR(100) DEFAULT 'Key Stakeholders'"),
        ("project_constraints_label", "VARCHAR(100) DEFAULT 'Project Constraints'"),
        ("cost_benefit_analysis_label", "VARCHAR(100) DEFAULT 'Cost-Benefit Analysis'")
    ]

    with app.app_context():
        with db.engine.connect() as conn:
            print("--- Starting BRD Schema Update ---")
            for col_name, col_def in new_columns:
                try:
                    # 'IF NOT EXISTS' is a safe way to run this multiple times without error
                    # Note: PostgreSQL supports IF NOT EXISTS for ADD COLUMN in newer versions.
                    # If you are on an older version and this fails, remove 'IF NOT EXISTS'.
                    sql = text(f"ALTER TABLE brd ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
                    conn.execute(sql)
                    print(f"[SUCCESS] Added column: {col_name}")
                except Exception as e:
                    print(f"[ERROR] Could not add {col_name}: {e}")
            
            conn.commit()
            print("--- Update Complete ---")

if __name__ == "__main__":
    add_columns()
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
                    # Using text() for raw SQL execution
                    sql = text(f"ALTER TABLE brd ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
                    conn.execute(sql)
                    print(f"[SUCCESS] Added column: {col_name}")
                except Exception as e:
                    print(f"[INFO] Could not add {col_name} (might already exist): {e}")
            
            conn.commit()
            print("--- Update Complete ---")

if __name__ == "__main__":
    add_columns()
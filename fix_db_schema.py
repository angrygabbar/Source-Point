from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

def fix_brd_table():
    """
    Adds missing label columns to the 'brd' table.
    Works for both SQLite and PostgreSQL.
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
        # 1. Inspect the database to find existing columns
        inspector = inspect(db.engine)
        
        # Check if table exists first
        if not inspector.has_table("brd"):
            print("[ERROR] Table 'brd' does not exist. Please run 'flask db upgrade' first.")
            return

        existing_columns = [col['name'] for col in inspector.get_columns('brd')]
        print(f"--- Checking 'brd' table in {db.engine.name} database ---")

        with db.engine.connect() as conn:
            # For SQLite, transactions are handled differently, so we use auto-commit logic
            trans = conn.begin()
            try:
                for col_name, col_def in new_columns:
                    if col_name not in existing_columns:
                        print(f"[FIXING] Adding missing column: {col_name}...")
                        # Add the column
                        conn.execute(text(f"ALTER TABLE brd ADD COLUMN {col_name} {col_def}"))
                        print(f"[SUCCESS] Added {col_name}")
                    else:
                        print(f"[OK] Column {col_name} already exists.")
                
                trans.commit()
                print("\n--- Schema Check Complete ---")
            except Exception as e:
                trans.rollback()
                print(f"\n[ERROR] Failed to update database: {str(e)}")

if __name__ == "__main__":
    fix_brd_table()
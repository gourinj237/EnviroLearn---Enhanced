
from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    inspector = inspect(db.engine)

    columns = [
        col["name"]
        for col in inspector.get_columns("challenge_submissions")
    ]

    migrations = {
        "ai_status": "VARCHAR(20)",
        "ai_confidence": "FLOAT",
        "ai_explanation": "TEXT"
    }

    with db.engine.begin() as connection:
        for column, datatype in migrations.items():
            if column not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE challenge_submissions "
                        f"ADD COLUMN {column} {datatype}"
                    )
                )
                print(f"Added column: {column}")
            else:
                print(f"Already exists: {column}")

    print("Database migration completed!")

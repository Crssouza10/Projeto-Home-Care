import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

queries = [
    "ALTER TABLE medications ADD COLUMN taken_status VARCHAR(20) DEFAULT 'pending'",
    "ALTER TABLE medications ADD COLUMN reminder_count INTEGER DEFAULT 0",
    "ALTER TABLE medications ADD COLUMN responsible_notified BOOLEAN DEFAULT FALSE",
    "ALTER TABLE medications ADD COLUMN last_taken_date DATE"
]

with engine.connect() as conn:
    for q in queries:
        try:
            conn.execute(text(q))
            conn.commit()
            print(f"Success: {q}")
        except Exception as e:
            conn.rollback()
            print(f"Already exists or error for {q}: {e.__class__.__name__}")

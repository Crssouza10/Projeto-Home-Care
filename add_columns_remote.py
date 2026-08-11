import os
from sqlalchemy import create_engine, text

# URL Remota do Supabase que estava no migrar_banco.py
REMOTE_URL = "postgresql://postgres.rmhiwdsqdbtedfrkubjo:Projetohomecare@aws-1-us-west-1.pooler.supabase.com:6543/postgres"

print("Connecting to REMOTE database...")
engine = create_engine(REMOTE_URL)

queries = [
    "ALTER TABLE medications ADD COLUMN taken_status VARCHAR(20) DEFAULT 'pending'",
    "ALTER TABLE medications ADD COLUMN reminder_count INTEGER DEFAULT 0",
    "ALTER TABLE medications ADD COLUMN responsible_notified BOOLEAN DEFAULT FALSE",
    "ALTER TABLE medications ADD COLUMN last_taken_date DATE",
    "ALTER TABLE responsibles ADD COLUMN notify_whatsapp BOOLEAN DEFAULT TRUE",
    "ALTER TABLE responsibles ADD COLUMN notify_call BOOLEAN DEFAULT FALSE"
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

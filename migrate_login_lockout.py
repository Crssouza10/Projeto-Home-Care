import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Defina DATABASE_URL no ambiente antes de rodar esta migração.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

queries = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP",
]

with engine.connect() as conn:
    for q in queries:
        try:
            conn.execute(text(q))
            conn.commit()
            print(f"OK: {q}")
        except Exception as e:
            conn.rollback()
            print(f"ERRO/EXISTE para {q}: {e.__class__.__name__}: {e}")

with engine.connect() as conn:
    res = conn.execute(text(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='users' AND column_name IN ('failed_login_attempts','locked_until')"
    ))
    print("Colunas de login lockout na tabela users:")
    for row in res:
        print(f"  - {row[0]}: {row[1]}")

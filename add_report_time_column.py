import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

LOCAL_URL = "postgresql://postgres:200466@localhost:5432/homecare_dev"
REMOTE_URL = "postgresql://postgres.rmhiwdsqdbtedfrkubjo:Projetohomecare@aws-1-us-west-1.pooler.supabase.com:6543/postgres"

def run_migration():
    print("Conectando aos bancos de dados...")
    engine_local = create_engine(LOCAL_URL)
    engine_remote = create_engine(REMOTE_URL)

    for name, engine in [("Local", engine_local), ("Remote", engine_remote)]:
        print(f"Migrando banco {name}...")
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN report_time VARCHAR(5)"))
                conn.commit()
                print(f"[OK] Coluna report_time adicionada com sucesso no banco {name}.")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"[INFO] Coluna report_time ja existe no banco {name}.")
                else:
                    print(f"[ERROR] Erro ao adicionar report_time no banco {name}: {e}")

if __name__ == "__main__":
    run_migration()

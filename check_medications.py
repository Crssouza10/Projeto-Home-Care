import os
from sqlalchemy import create_engine, text

REMOTE_URL = 'postgresql://postgres.rmhiwdsqdbtedfrkubjo:Projetohomecare@aws-1-us-west-1.pooler.supabase.com:6543/postgres'
LOCAL_URL = 'postgresql://postgres:200466@localhost:5432/homecare_dev'

print("--- VERIFICANDO DADOS REMOTOS (SUPABASE) ---")
try:
    engine = create_engine(REMOTE_URL)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, name, dosage, time FROM medications"))
        meds = res.fetchall()
        print(f"Total de medicamentos no Supabase: {len(meds)}")
        for m in meds:
            print(f" - {m[1]} ({m[2]}) às {m[3]}")
except Exception as e:
    print("Erro Supabase:", e)

print("\n--- APLICANDO CORREÇÃO NO BANCO DE DADOS (LOCAL E REMOTO) ---")
for url, env in [(LOCAL_URL, "LOCAL"), (REMOTE_URL, "SUPABASE")]:
    try:
        e = create_engine(url)
        with e.connect() as conn:
            conn.execute(text("ALTER TABLE medications ADD COLUMN IF NOT EXISTS is_continuous BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print(f"[{env}] Coluna is_continuous adicionada com sucesso!")
    except Exception as ex:
        print(f"[{env}] Erro ou coluna ja existe:", ex)

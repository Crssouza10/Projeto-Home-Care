"""
Adiciona colunas start_date e continuous_months na tabela medications.
Executar: python add_review_columns.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app import engine

with engine.connect() as conn:
    # Adicionar start_date
    try:
        conn.execute(text("ALTER TABLE medications ADD COLUMN start_date VARCHAR(10)"))
        conn.commit()
        print("✅ Coluna start_date adicionada.")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("ℹ️  Coluna start_date já existe.")
        else:
            print(f"⚠️  Erro ao adicionar start_date: {e}")

    # Adicionar continuous_months
    try:
        conn.execute(text("ALTER TABLE medications ADD COLUMN continuous_months INTEGER DEFAULT 6"))
        conn.commit()
        print("✅ Coluna continuous_months adicionada.")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("ℹ️  Coluna continuous_months já existe.")
        else:
            print(f"⚠️  Erro ao adicionar continuous_months: {e}")

    # Atualizar medicamentos contínuos existentes: usar created_at como start_date se nulo
    result = conn.execute(text(
        "UPDATE medications SET start_date = to_char(created_at, 'YYYY-MM-DD') "
        "WHERE is_continuous = true AND start_date IS NULL"
    ))
    conn.commit()
    print(f"✅ Medicamentos contínuos atualizados: {result.rowcount} registro(s)")

    # Verificar
    result = conn.execute(text(
        "SELECT id, name, is_continuous, start_date, continuous_months FROM medications"
    ))
    for r in result.fetchall():
        print(f"   {r[1]:25s} | contínuo={r[2]} | start={r[3]} | meses={r[4]}")

print("\n✅ Migração concluída.")

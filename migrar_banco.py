import sys
import os
import sqlalchemy.orm.session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importa os modelos e a Base do arquivo app.py
from app import Base, User, EmergencyContact, Medication, Appointment, Responsible

# URLs dos bancos
LOCAL_URL = "postgresql://postgres:200466@localhost:5432/homecare_dev"
REMOTE_URL = "postgresql://postgres.rmhiwdsqdbtedfrkubjo:Projetohomecare@aws-1-us-west-1.pooler.supabase.com:6543/postgres"

def main():
    print("Conectando aos bancos de dados...")
    engine_local = create_engine(LOCAL_URL)
    engine_remote = create_engine(REMOTE_URL)

    print("Criando tabelas no Supabase...")
    Base.metadata.create_all(bind=engine_remote)
    
    SessionLocal = sessionmaker(bind=engine_local)
    SessionRemote = sessionmaker(bind=engine_remote)
    
    session_l = SessionLocal()
    session_r = SessionRemote()

    modelos = [
        User,
        EmergencyContact,
        Medication,
        Appointment,
        Responsible
    ]

    print("Iniciando a cópia dos dados...")
    for model in modelos:
        print(f"Migrando dados da tabela: {model.__tablename__}...")
        registros = session_l.query(model).all()
        
        count = 0
        for r in registros:
            # Remove o objeto da sessão local para que seja tratado como novo
            session_l.expunge(r)
            sqlalchemy.orm.session.make_transient(r)
            
            # O merge vai inserir ou atualizar mantendo o UUID original
            session_r.merge(r)
            count += 1
            
        session_r.commit()
        print(f"  -> {count} registros copiados.")

    print("\n✅ Migração concluída com sucesso! O banco na nuvem agora tem todos os seus dados e tabelas.")

if __name__ == "__main__":
    main()

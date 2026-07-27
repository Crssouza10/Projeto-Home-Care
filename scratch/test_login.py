import sys
import os
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import User, Base

DATABASE_URL = "postgresql://postgres.rmhiwdsqdbtedfrkubjo:Projetohomecare@aws-1-us-west-1.pooler.supabase.com:6543/postgres"

print("Tentando conectar ao banco...")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

username = "conta gratis"
print(f"Buscando usuário '{username}'...")
try:
    user = db.query(User).filter(
        or_(
            User.full_name.ilike(f"%{username}%"),
            User.phone == username,
            User.email == username
        ),
        User.is_active == True
    ).first()
    
    if user:
        print("Usuário encontrado!")
        print(f"ID: {user.id}")
        print(f"Nome completo: {user.full_name}")
        print(f"E-mail: {user.email}")
        print(f"Telefone: {user.phone}")
        print(f"Password hash: {user.password_hash}")
    else:
        print("Usuário não encontrado.")
except Exception as e:
    print("Ocorreu um erro ao buscar o usuário:")
    import traceback
    traceback.print_exc()
finally:
    db.close()

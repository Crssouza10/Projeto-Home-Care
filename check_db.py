import os
import sys

from app import Base, engine as local_engine
from sqlalchemy import create_engine, text

REMOTE_URL = 'postgresql://postgres.rmhiwdsqdbtedfrkubjo:Projetohomecare@aws-1-us-west-1.pooler.supabase.com:6543/postgres'
remote_engine = create_engine(REMOTE_URL)

try:
    with remote_engine.connect() as conn:
        print('--- Testando conexao com Supabase ---')
        
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tabelas = [row[0] for row in result]
        print('Tabelas no Supabase:', tabelas)
        
        if 'push_subscriptions' not in tabelas:
            print('Tabela push_subscriptions NAO EXISTE no Supabase! Criando agora...')
            Base.metadata.create_all(bind=remote_engine)
            print('Tabela criada com sucesso!')
        else:
            print('A tabela push_subscriptions JA EXISTE no Supabase!')
            
        res = conn.execute(text("SELECT id, endpoint, created_at FROM push_subscriptions"))
        inscricoes = res.fetchall()
        print('--- INSCRICOES CADASTRADAS NO SUPABASE ---')
        print(f'Total: {len(inscricoes)}')
        for insc in inscricoes:
            print(f'ID: {insc[0]} | Endpoint: {insc[1][:30]}... | Criado em: {insc[2]}')
            
except Exception as e:
    print('Erro fatal:', e)

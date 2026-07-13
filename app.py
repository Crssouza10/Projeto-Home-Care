# ===== versão 2.30 - 2026-07-13 ================================
import sys
# Garante codificação UTF-8 para evitar erros de unicode no console (especialmente no Windows)
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from fastapi import FastAPI, HTTPException, Depends, status, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles  # ✅ IMPORTAÇÃO CRÍTICA!
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Time, Date, Text, or_, Integer, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime, time, date, timedelta, timezone
from dotenv import load_dotenv
from pywebpush import webpush, WebPushException
from gtts import gTTS
from hashlib import sha256
from pathlib import Path
import os
import uuid
import json
import re
import asyncio
import traceback
import requests  # Para WhatsApp API
import io
import urllib.parse
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import httpx
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
# scheduler_engine - motor de recorrência (regras 5a-5d)
from scheduler_engine import generate_medication_schedules, get_schedule_summary, is_review_needed, get_review_date
# pytesseract e PIL
try:
    import pytesseract
    from PIL import Image
    if sys.platform.startswith('win'):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    os.environ['TESSDATA_PREFIX'] = os.path.join(os.path.dirname(__file__), 'tessdata')
except Exception as e:
    print(f"Aviso: pytesseract ou PIL não puderam ser inicializados ({e})")


# ===== CONFIGURAÇÃO PARA VERCEL =====
IS_VERCEL = os.getenv('VERCEL', '0') == '1'
if IS_VERCEL:
    sys.path.append(os.getcwd())

# Carrega variáveis de ambiente ANTES de usar
load_dotenv(override=True)

# ===== CRIAÇÃO DO APP (APENAS UMA VEZ) =====
app = FastAPI(
    title="CR$ HOME CARE AI",
    description="Sistema de Cuidado Domiciliar Inteligente",
    version="1.0.4"
)

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ARQUIVOS ESTÁTICOS =====
# Na Vercel, filesystem é read-only — estáticos são servidos pelo próprio deploy
if not IS_VERCEL:
    os.makedirs("static/audio", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== BANCO DE DADOS =====
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback para o banco Supabase de produção/homologação para evitar crash na Vercel
    DATABASE_URL = "postgresql://postgres.rmhiwdsqdbtedfrkubjo:Projetohomecare@aws-1-us-west-1.pooler.supabase.com:6543/postgres"
    print("⚠️ DATABASE_URL não configurada. Utilizando fallback do Supabase.")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"DATABASE_URL: {'Configurada' if DATABASE_URL else 'NAO CONFIGURADA'}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Garante que a coluna box_image existe na tabela medications
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE medications ADD COLUMN IF NOT EXISTS box_image TEXT;"))
        conn.commit()
        print("✅ Coluna box_image verificada/adicionada com sucesso na tabela medications.")
except Exception as e:
    print(f"⚠️ Erro ao verificar/adicionar coluna box_image: {e}")

# Garante que as colunas de informações clínicas existem na tabela users
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS age INTEGER;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS allergies TEXT;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS conditions TEXT;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS blood_type VARCHAR(10);"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS health_insurance VARCHAR(100);"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS health_insurance_card TEXT;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS identity_document VARCHAR(100);"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS identity_document_file TEXT;"))
        conn.commit()
        print("✅ Colunas clínicas adicionadas/verificadas com sucesso na tabela users.")
except Exception as e:
    print(f"⚠️ Erro ao verificar/adicionar colunas clínicas na tabela users: {e}")

# Garante que a tabela medication_schedules existe
try:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS medication_schedules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                medication_id UUID NOT NULL,
                user_id UUID NOT NULL,
                scheduled_date DATE NOT NULL,
                scheduled_time TIME NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_schedules_med_id ON medication_schedules(medication_id);
            CREATE INDEX IF NOT EXISTS idx_schedules_user_id ON medication_schedules(user_id);
            CREATE INDEX IF NOT EXISTS idx_schedules_date ON medication_schedules(scheduled_date);
        """))
        conn.commit()
        print("✅ Tabela medication_schedules verificada/criada com sucesso.")
except Exception as e:
    print(f"⚠️ Erro ao verificar/criar tabela medication_schedules: {e}")


# ==================== MODELOS (TABELAS) ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # ou datetime.utcnow se mudar o import
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # NOVAS COLUNAS CLÍNICAS
    age = Column(Integer, nullable=True)
    allergies = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)
    blood_type = Column(String(10), nullable=True)
    health_insurance = Column(String(100), nullable=True)
    health_insurance_card = Column(Text, nullable=True)
    identity_document = Column(String(100), nullable=True)
    identity_document_file = Column(Text, nullable=True)

class Medication(Base):
    __tablename__ = "medications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    dosage = Column(String(50), nullable=False)
    time = Column(Time, nullable=False)
    days_of_week = Column(JSONB, default=[0,1,2,3,4,5,6])
    is_active = Column(Boolean, default=True)
    is_continuous = Column(Boolean, default=False)
    continuous_months = Column(Integer, default=6)
    start_date = Column(String(10), nullable=True)  # "YYYY-MM-DD" data de início do tratamento
    created_at = Column(DateTime, default=datetime.utcnow)
    end_date = Column(String(10), nullable=True)  # "YYYY-MM-DD" ou use Date
    
    # NOVAS COLUNAS DO FLUXO DE ESTADO
    taken_status = Column(String(20), default="pending")
    reminder_count = Column(Integer, default=0)
    responsible_notified = Column(Boolean, default=False)
    last_taken_date = Column(Date, nullable=True)
    box_image = Column(Text, nullable=True)

# -------------------------------------------------------
# MODELO PARA PUSH SUBSCRIPTIONS (TABELA NOVA)
# -------------------------------------------------------
class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint = Column(Text, unique=True, nullable=False, index=True)
    keys = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# class Prescription(Base):
#    __tablename__ = "prescriptions"
#    
#    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
#    image_url = Column(String(500), nullable=False)
#    ocr_data = Column(JSONB)
#    extracted_meds = Column(JSONB)
#    status = Column(String(20), default="pending")
#    created_at = Column(DateTime, default=datetime.utcnow)  # ou datetime.utcnow se mudar o import


class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    doctor_name = Column(String(100), nullable=False)
    specialty = Column(String(80))
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    notes = Column(Text)
    status = Column(String(20), default="scheduled")
    created_at = Column(DateTime, default=datetime.utcnow)  # ou datetime.utcnow se mudar o import


class Responsible(Base):
    __tablename__ = "responsibles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    relationship = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    notify_sms = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=False)
    notify_whatsapp = Column(Boolean, default=True)
    notify_call = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)  # ou datetime.utcnow se mudar o import


class MedicationLog(Base):
    __tablename__ = "medication_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    medication_id = Column(UUID(as_uuid=True))
    scheduled_datetime = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")
    confirmed_at = Column(DateTime)
    followup_triggered_at = Column(DateTime)
    responsible_notified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)  # ou datetime.utcnow se mudar o import


# Modelo de Contatos de Emergência (APENAS 1x)
class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    contact_type = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # ou datetime.utcnow se mudar o import


# ==================== NOVO MODELO: MedicationSchedule ====================
# Armazena cada ocorrência individual de um medicamento (suporte às regras 5a-5d)
class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time, nullable=False)
    status = Column(String(20), default="pending")  # pending, taken, skipped, cancelled
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== PYDANTIC SCHEMAS ====================

class UserCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ClinicalInfoUpdate(BaseModel):
    age: Optional[int] = None
    allergies: Optional[str] = None
    conditions: Optional[str] = None
    blood_type: Optional[str] = None
    health_insurance: Optional[str] = None
    health_insurance_card: Optional[str] = None
    identity_document: Optional[str] = None
    identity_document_file: Optional[str] = None

class MedicationCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    dosage: str
    time: str
    days_of_week: List[int] = [0,1,2,3,4,5,6]
    is_continuous: bool = False
    continuous_months: int = 6
    duration_days: Optional[int] = None
    end_date: Optional[str] = None
    start_date: Optional[str] = None

from typing import Optional, List  # ✅ Certifique-se que este import existe no topo do arquivo

class MedicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    dosage: str
    time: time
    days_of_week: List[int]  # ✅ Tipo correto: lista de inteiros
    periodo: Optional[str] = None
    
    # ✅ CAMPOS QUE ESTAVAM FALTANDO (CRÍTICOS PARA O FLUXO DE 7 ESTADOS):
    taken_status: Optional[str] = "pending"  # "pending", "taken", "rescheduled", "not_taken"
    is_active: Optional[bool] = True          # ✅ Torna opcional com valor padrão
    reminder_count: Optional[int] = 0
    responsible_notified: Optional[bool] = False
    last_taken_date: Optional[date] = None
    box_image: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class AppointmentCreate(BaseModel):
    user_id: uuid.UUID
    doctor_name: str
    specialty: Optional[str] = None
    appointment_date: date
    appointment_time: time
    notes: Optional[str] = None

class ResponsibleCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    relationship: str
    phone: str
    notify_sms: bool = True
    notify_email: bool = True 
    notify_whatsapp: Optional[bool] = True
    notify_call: Optional[bool] = False

# Schemas para Cliente (Paciente)
class ClienteLogin(BaseModel):
    username: str
    password: str

class ClienteMedicationResponse(BaseModel):
    id: str
    name: str
    dosage: str
    time: str
    periodo: str
    days_of_week: list
    taken_status: Optional[str] = "pending"
    is_active: Optional[bool] = True
    is_continuous: Optional[bool] = False
    start_date: Optional[str] = None
    created_at: Optional[str] = None
    end_date: Optional[str] = None
    last_taken_date: Optional[date] = None
    box_image: Optional[str] = None
    is_review_needed: Optional[bool] = False
    review_date: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ClienteAppointmentResponse(BaseModel):
    id: str
    doctor_name: str
    specialty: Optional[str]
    appointment_date: str
    appointment_time: str
    status: str
    model_config = ConfigDict(from_attributes=True)

class ClienteResponsibleResponse(BaseModel):
    id: str
    name: str
    relationship: str
    phone: str
    notify_sms: bool
    notify_whatsapp: Optional[bool] = True
    notify_call: Optional[bool] = False
    model_config = ConfigDict(from_attributes=True)

# Schema para Contatos de Emergência (APENAS 1x)
class EmergencyContactCreate(BaseModel):
    name: str
    type: str  # Frontend envia 'type'
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: list = []

class ForgotPasswordRequest(BaseModel):
    contact: str

class PushSubscriptionCreate(BaseModel):
    user_id: str
    endpoint: str
    keys: dict



# ==================== DEPENDENCIES ====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== FUNÇÕES AUXILIARES ====================

def _get_periodo(time_val):
    """Converte horário em período do dia"""
    try:
        if isinstance(time_val, str):
            hora = int(time_val.split(':')[0])
        else:
            hora = time_val.hour
        if 5 <= hora < 12: return "Manhã"
        elif 12 <= hora < 18: return "Tarde"
        elif 18 <= hora < 24: return "Noite"
        else: return "Madrugada"
    except:
        return "Não definido"

# ==================== ROTAS ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = str(exc)
    print(f"🔥 ERRO FATAL: {error_msg}")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro do Servidor: {error_msg}"}
    )

# --- FRONTEND ---
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_file = Path(__file__).parent / "index.html"
    if not html_file.exists():
        return HTMLResponse(content="<h1>Erro: index.html não encontrado</h1>", status_code=500)
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    html_file = Path(__file__).parent / "dashboard.html"
    if not html_file.exists():
        return HTMLResponse(content="<h1>Erro: dashboard.html não encontrado</h1>", status_code=500)
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))

@app.get("/dashboard-cliente", response_class=HTMLResponse)
async def serve_dashboard_cliente():
    html_file = Path(__file__).parent / "dashboard_cliente.html"
    if not html_file.exists():
        return HTMLResponse(content="<h1>Erro: dashboard_cliente.html não encontrado</h1>", status_code=500)
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))

# --- HEALTH CHECK ---
@app.get("/health")
async def health_check():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "database": "connected", "message": "CR$ HOME CARE AI - Sistema operacional"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

# =========================================================
# 📅 HISTÓRICO DE MEDICAMENTOS POR DATA
# =========================================================
@app.get("/api/cliente/{user_id}/medications/history")
async def get_medication_history(user_id: str, date: str, db: Session = Depends(get_db)):
    """
    Retorna medicamentos agendados para uma data específica
    """
    try:
        user_uuid = uuid.UUID(user_id)
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Converte para dia da semana (0=Dom, 6=Sáb)
        day_of_week = target_date.weekday()
        if day_of_week == 6:  # Python: 0=Seg, 6=Dom
            day_of_week = 0
        else:
            day_of_week += 1
        
        print(f"🔍 Buscando histórico para {date} (dia da semana: {day_of_week})")
        
        # Fim do dia selecionado (para incluir todos os registros daquela data)
        target_date_end = datetime.combine(target_date, time(23, 59, 59))
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        # Busca medicamentos ativos que incluem este dia e foram criados antes ou no próprio dia, e que não estejam vencidos
        medications = db.query(Medication).filter(
            Medication.user_id == user_uuid,
            Medication.is_active == True,
            Medication.created_at <= target_date_end,
            or_(
                Medication.end_date == None,
                Medication.end_date >= target_date_str
            ),
            or_(
                Medication.days_of_week.contains([day_of_week]),
                Medication.days_of_week == []
            )
        ).all()
        
        print(f"✅ {len(medications)} medicamentos encontrados")
        
        # ✅ CORREÇÃO: Usa scheduled_datetime e confirmed_at (nomes corretos!)
        logs_query = text("""
            SELECT medication_id, status, confirmed_at
            FROM medication_logs
            WHERE user_id = :user_id
            AND CAST(scheduled_datetime AS DATE) = :target_date
        """)
        logs_result = db.execute(logs_query, {
            "user_id": user_uuid,
            "target_date": target_date
        })
        
        logs_dict = {}
        for log in logs_result:
            logs_dict[str(log[0])] = {
                "status": log[1],
                "actual_time": log[2].strftime("%H:%M") if log[2] else None
            }
        
        resultado = []
        for med in medications:
            med_id = str(med.id)
            log = logs_dict.get(med_id, {})
            
            resultado.append({
                "id": med_id,
                "name": med.name,
                "dosage": med.dosage,
                "time": med.time.strftime("%H:%M") if med.time else None,
                "days_of_week": med.days_of_week or [],
                "taken_status": log.get("status", "pending"),
                "taken_time": log.get("actual_time"),
                "created_at": med.created_at.strftime("%Y-%m-%d") if med.created_at else None,
                "end_date": med.end_date,
                "is_history": True,
                "box_image": med.box_image
            })
        
        return resultado
        
    except Exception as e:
        print(f"❌ Erro ao carregar histórico: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
# =========================================================
# 🔐 AUTH - LOGIN DO CLIENTE
# =========================================================
@app.post("/api/cliente/login")
async def cliente_login(credentials: dict, db: Session = Depends(get_db)):
    username = credentials.get('username')
    password = credentials.get('password')
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuário e senha obrigatórios")
    
    user = db.query(User).filter(
        or_(
            User.full_name.ilike(f"%{username}%"),
            User.phone == username,
            User.email == username
        ),
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    
    password_hash = sha256(password.encode()).hexdigest()
    if user.password_hash != password_hash:
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    return {
        "status": "sucesso",
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone
        }
    }

@app.get("/api/cliente/{user_id}/clinical-info")
async def get_clinical_info(user_id: str, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    return {
        "age": user.age,
        "allergies": user.allergies,
        "conditions": user.conditions,
        "blood_type": user.blood_type,
        "health_insurance": user.health_insurance,
        "health_insurance_card": user.health_insurance_card,
        "identity_document": user.identity_document,
        "identity_document_file": user.identity_document_file,
        "full_name": user.full_name,
        "phone": user.phone,
        "email": user.email
    }

@app.put("/api/cliente/{user_id}/clinical-info")
async def update_clinical_info(user_id: str, info: ClinicalInfoUpdate, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user.age = info.age
    user.allergies = info.allergies
    user.conditions = info.conditions
    user.blood_type = info.blood_type
    user.health_insurance = info.health_insurance
    user.health_insurance_card = info.health_insurance_card
    user.identity_document = info.identity_document
    user.identity_document_file = info.identity_document_file
    db.commit()
    
    return {
        "status": "success",
        "message": "Informações clínicas atualizadas com sucesso"
    }

# ========================================================
# NOVA ROTA: Gerar Áudio TTS (Sem Google Cloud Key!)
# ========================================================
@app.post("/api/generate-audio")
async def generate_audio(request: dict):
    try:
        # 1. Extrair dados do medicamento
        medication = request.get("medication", "Seu medicamento")
        dosage = request.get("dosage", "conforme prescrição")
        instructions = request.get("instructions", "")
        
        # 2. Codificar parâmetros para uma URL segura
        params = urllib.parse.urlencode({
            "medication": medication,
            "dosage": dosage,
            "instructions": instructions
        })
        
        # 3. Retornar a URL dinâmica de streaming de áudio
        audio_url = f"/api/serve-audio?{params}"
        
        return {"status": "success", "url": audio_url, "message": "Áudio preparado com sucesso!"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/serve-audio")
async def serve_audio(medication: str = "Seu medicamento", dosage: str = "conforme prescrição", instructions: str = ""):
    try:
        # 1. Montar o texto a partir dos parâmetros da query string (personalizado para consulta)
        if medication == "Consulta Médica":
            text = f"Atenção! Lembrete de consulta. {instructions}"
        else:
            text = f"Atenção! Lembrete de medicamento. Hora de tomar: {medication}, {dosage}. {instructions}"
        
        # 2. Gerar áudio com gTTS (Google Text-to-Speech)
        tts = gTTS(text=text, lang='pt-br', slow=False)
        
        # 3. Salvar o áudio em um buffer de memória
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        # 4. Retornar o buffer como Stream de áudio
        return StreamingResponse(fp, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# =========================================================
# 💊 CRUD MEDICAÇÕES
# =========================================================

@app.get("/api/cliente/{user_id}/medications", response_model=List[ClienteMedicationResponse])
async def get_client_medications(user_id: str, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    medications = db.query(Medication).filter(
        Medication.user_id == user_uuid,
        Medication.is_active == True,
        or_(
            Medication.end_date == None,
            Medication.end_date >= today_str
        )
    ).all()
    
    resultado = []
    today_date = datetime.now().date()
    
    for med in medications:
        status = med.taken_status
        # Se foi tomado em um dia anterior, resetamos para pending na resposta
        if status == 'taken' and med.last_taken_date != today_date:
            status = 'pending'
            
        resultado.append({
            "id": str(med.id),
            "name": med.name,
            "dosage": med.dosage,
            "time": med.time.strftime('%H:%M') if med.time else None,
            "periodo": _get_periodo(med.time),
            "days_of_week": med.days_of_week if med.days_of_week is not None else [],
            "taken_status": status,
            "is_active": med.is_active,
            "is_continuous": med.is_continuous,
            "start_date": med.start_date,
            "created_at": med.created_at.strftime("%Y-%m-%d") if med.created_at else None,
            "end_date": med.end_date.isoformat() if hasattr(med.end_date, 'isoformat') else (str(med.end_date) if med.end_date else None),
            "last_taken_date": med.last_taken_date.isoformat() if med.last_taken_date else None,
            "box_image": med.box_image,
            # Revisão para medicamentos contínuos
            "is_review_needed": is_review_needed(
                datetime.strptime(med.start_date, "%Y-%m-%d").date(),
                med.continuous_months
            ) if med.is_continuous and med.start_date else False,
            "review_date": get_review_date(
                datetime.strptime(med.start_date, "%Y-%m-%d").date(),
                med.continuous_months
            ).isoformat() if med.is_continuous and med.start_date else None,
        })
    
    return resultado

def get_actual_start_date(start_date: date, days_of_week: list) -> date:
    if not days_of_week:
        return start_date
    for i in range(7):
        candidate = start_date + timedelta(days=i)
        py_day = candidate.weekday()
        custom_day = 0 if py_day == 6 else py_day + 1
        if custom_day in days_of_week:
            return candidate
    return start_date

# ===== DISTRIBUIÇÃO DE HORÁRIOS PARA EVITAR INTOXICAÇÃO =====
def distribute_time(user_id, preferred_time_str: str, db: Session, current_med_id=None) -> str:
    """
    Verifica se já existe medicamento ativo no mesmo horário para o usuário.
    Se houver conflito, adiciona 15 minutos até encontrar horário livre.
    
    Regra de segurança: evita múltiplos medicamentos no mesmo minuto
    para prevenir intoxicação por ingestão simultânea.
    """
    from datetime import timedelta
    
    try:
        base_time = datetime.strptime(preferred_time_str, "%H:%M").time()
    except ValueError:
        return preferred_time_str  # Se não conseguir parsear, mantém original
    
    # Horário limite: não passar das 23:45
    max_time = time(23, 45)
    max_attempts = 8  # Máximo 2 horas de distribuição (8 × 15 min)
    
    check_time = base_time
    for attempt in range(max_attempts):
        time_str = check_time.strftime("%H:%M")
        
        # Consulta medicamentos ativos do usuário neste horário
        query = db.query(Medication).filter(
            Medication.user_id == user_id,
            Medication.time == time_str,
            # Medicamento ativo: sem end_date OU end_date >= hoje
            (Medication.end_date == None) | (Medication.end_date >= date.today().strftime("%Y-%m-%d"))
        )
        if current_med_id:
            query = query.filter(Medication.id != current_med_id)
        
        existing = query.first()
        
        if not existing:
            # Horário livre!
            if attempt > 0:
                print(f"⏰ Horário {preferred_time_str} ocupado → ajustado para {time_str} (tentativa {attempt})")
            return time_str
        
        # Avança 15 minutos
        dummy_dt = datetime.combine(date.today(), check_time) + timedelta(minutes=15)
        check_time = dummy_dt.time()
        
        # Se passou das 23:45, volta para o início da manhã seguinte
        if check_time > max_time:
            break
    
    # Se todos os horários estiverem ocupados, retorna o preferido mesmo assim
    # (melhor que não criar o medicamento)
    print(f"⚠️ Todos os horários ocupados para {preferred_time_str} — mantendo original")
    return preferred_time_str

@app.post("/api/cliente/{user_id}/medications", status_code=status.HTTP_201_CREATED)
async def create_medication(user_id: str, med: MedicationCreate, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    # 1. Determinar a data de início com base no start_date recebido (ou hoje se nulo)
    start_dt = date.today()
    if getattr(med, 'start_date', None):
        try:
            start_dt = datetime.strptime(med.start_date, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    # 2. Calcular a primeira ocorrência real baseada nos dias da semana
    actual_start = get_actual_start_date(start_dt, med.days_of_week)
    
    # 3. Calcular data final do tratamento
    end_date = None
    if hasattr(med, 'is_continuous') and med.is_continuous:
        end_date = None  # Contínuo não tem data final
    elif hasattr(med, 'duration_days') and med.duration_days is not None and med.duration_days > 0:
        end_date = (actual_start + timedelta(days=med.duration_days - 1)).strftime("%Y-%m-%d")
    
    # 4. 🛡️ Distribuir horário para evitar intoxicação (múltiplos medicamentos no mesmo horário)
    adjusted_time = distribute_time(user_uuid, med.time, db)
    
    # 5. Criar o medicamento
    nova_med = Medication(
        user_id=user_uuid,
        name=med.name,
        dosage=med.dosage,
        time=adjusted_time,
        days_of_week=med.days_of_week,
        is_continuous=getattr(med, 'is_continuous', False),
        continuous_months=getattr(med, 'continuous_months', 6),
        start_date=actual_start.strftime("%Y-%m-%d"),
        end_date=end_date,
        created_at=datetime.combine(actual_start, time(0, 0, 0))
    )
    
    db.add(nova_med)
    db.flush()  # Garante que nova_med.id esteja disponível
    
    # 6. ✅ NOVO: Gerar schedules automaticamente usando o scheduler_engine
    time_obj = datetime.strptime(adjusted_time, "%H:%M").time() if isinstance(adjusted_time, str) else adjusted_time
    schedules = generate_medication_schedules(
        user_id=user_uuid,
        medication_id=nova_med.id,
        med_time=time_obj,
        days_of_week=med.days_of_week if med.days_of_week else [0, 1, 2, 3, 4, 5, 6],
        start_date=actual_start,
        duration_days=getattr(med, 'duration_days', None),
        is_continuous=getattr(med, 'is_continuous', False),
    )
    
    # Inserir schedules no banco
    for s in schedules:
        db.add(MedicationSchedule(
            medication_id=nova_med.id,
            user_id=user_uuid,
            scheduled_date=s["scheduled_date"],
            scheduled_time=s["scheduled_time"],
            status=s["status"],
        ))
    
    db.commit()
    db.refresh(nova_med)
    
    # Resumo para o frontend
    summary = get_schedule_summary(schedules, med.days_of_week, actual_start, 
                                   datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None)
    
    # Verifica se o horário foi ajustado
    horario_ajustado = adjusted_time != med.time
    
    return {
        "status": "sucesso",
        "id": str(nova_med.id),
        "schedules_gerados": len(schedules),
        "resumo": summary,
        "time": adjusted_time,
        "time_original": med.time if horario_ajustado else None,
        "horario_ajustado": horario_ajustado,
        "aviso": f"⏰ Horário ajustado de {med.time} para {adjusted_time} para evitar intoxicação" if horario_ajustado else None,
    }


# =========================================================
#  ROTAS DE ESTADO DO MEDICAMENTO (FLUXO DE 7 ESTADOS)
# =========================================================

# =========================================================
# 📅 NOVAS ROTAS: MEDICATION SCHEDULES
# =========================================================

@app.get("/api/medications/{med_id}/schedules")
async def get_medication_schedules(med_id: str, db: Session = Depends(get_db)):
    """Lista todos os schedules de um medicamento (histórico completo)"""
    try:
        med_uuid = uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    schedules = db.query(MedicationSchedule).filter(
        MedicationSchedule.medication_id == med_uuid
    ).order_by(MedicationSchedule.scheduled_date).all()
    
    return [{
        "id": str(s.id),
        "scheduled_date": s.scheduled_date.isoformat(),
        "scheduled_time": s.scheduled_time.strftime("%H:%M"),
        "status": s.status,
        "confirmed_at": s.confirmed_at.isoformat() if s.confirmed_at else None,
    } for s in schedules]


@app.get("/api/medications/{med_id}/schedules/count")
async def count_future_schedules(med_id: str, db: Session = Depends(get_db)):
    """Conta quantos schedules futuros (hoje em diante) existem - para o modal de delete"""
    try:
        med_uuid = uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    today = date.today()
    
    total = db.query(MedicationSchedule).filter(
        MedicationSchedule.medication_id == med_uuid
    ).count()
    
    past = db.query(MedicationSchedule).filter(
        MedicationSchedule.medication_id == med_uuid,
        MedicationSchedule.scheduled_date < today
    ).count()
    
    future = db.query(MedicationSchedule).filter(
        MedicationSchedule.medication_id == med_uuid,
        MedicationSchedule.scheduled_date >= today
    ).count()
    
    future_pending = db.query(MedicationSchedule).filter(
        MedicationSchedule.medication_id == med_uuid,
        MedicationSchedule.scheduled_date >= today,
        MedicationSchedule.status == "pending"
    ).count()
    
    return {
        "total": total,
        "passados": past,
        "futuros": future,
        "futuros_pendentes": future_pending,
    }


@app.post("/api/schedules/{schedule_id}/take")
async def mark_schedule_taken(schedule_id: str, db: Session = Depends(get_db)):
    """Marca um schedule específico como tomado (NOVO - por ocorrência)"""
    try:
        sched_uuid = uuid.UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    sched = db.query(MedicationSchedule).filter(
        MedicationSchedule.id == sched_uuid
    ).first()
    
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule não encontrado")
    
    sched.status = "taken"
    sched.confirmed_at = datetime.now()
    
    # Também atualiza o medication_log para compatibilidade
    db.add(MedicationLog(
        user_id=sched.user_id,
        medication_id=sched.medication_id,
        scheduled_datetime=datetime.combine(sched.scheduled_date, sched.scheduled_time),
        status="taken",
        confirmed_at=datetime.now(),
    ))
    
    db.commit()
    
    return {"status": "success", "message": "✅ Registrado como tomado"}

@app.post("/api/medications/{med_id}/take")
async def mark_taken(med_id: str):
    """Estado 3 ou 6: Marca como tomado e encerra monitoramento do dia"""
    db = SessionLocal()
    try:
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med: raise HTTPException(404, "Medicamento não encontrado")
        
        med.taken_status = "taken"
        med.last_taken_date = datetime.now().date()
        med.reminder_count = 0
        med.responsible_notified = False
        
        if med.time:
            sched_dt = datetime.combine(datetime.now().date(), med.time)
        else:
            sched_dt = datetime.now()
            
        new_log = MedicationLog(
            user_id=med.user_id,
            medication_id=med.id,
            scheduled_datetime=sched_dt,
            status="taken",
            confirmed_at=datetime.now()
        )
        db.add(new_log)
        db.commit()
        
        return {"status": "success", "message": "✅ Registrado como tomado"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    finally:
        db.close()

# =========================================================
# Endpoint para reagendar medicamento
# =========================================================

@app.put("/api/medications/{med_id}/reschedule")
async def reschedule_medication(med_id: str, new_time: str):
    """Estado 4: Reagenda e muda status para aguardar novo horário"""
    db = SessionLocal()
    try:
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med: raise HTTPException(404, "Medicamento não encontrado")
        
        h, m = map(int, new_time.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Horário inválido")
            
        med.time = time(h, m)
        med.taken_status = "rescheduled"
        med.reminder_count = 0
        db.commit()
        
        return {"status": "success", "new_time": f"{h:02d}:{m:02d}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(400 if "inválido" in str(e) else 500, str(e))
    finally:
        db.close()

@app.post("/api/medications/{med_id}/not-taken")
async def mark_not_taken(med_id: str):
    """Estado 7: Não tomado no reagendamento -> Aciona responsável"""
    db = SessionLocal()
    try:
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med: raise HTTPException(404, "Medicamento não encontrado")
        
        med.taken_status = "not_taken"
        med.responsible_notified = True
        med.reminder_count += 1
        
        if med.time:
            sched_dt = datetime.combine(datetime.now().date(), med.time)
        else:
            sched_dt = datetime.now()
            
        new_log = MedicationLog(
            user_id=med.user_id,
            medication_id=med.id,
            scheduled_datetime=sched_dt,
            status="not_taken",
            confirmed_at=datetime.now(),
            responsible_notified_at=datetime.now()
        )
        db.add(new_log)
        db.commit()
        
        #  Dispara notificação (assíncrono para não travar UI)
        asyncio.create_task(notify_responsible_async(med.id))
        
        return {"status": "success", "message": "❌ Não tomado. Responsável acionado."}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    finally:
        db.close()
 
@app.put("/api/medications/{med_id}/box-image")
async def save_medication_box_image(med_id: str, data: dict, db: Session = Depends(get_db)):
    try:
        med_uuid = uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de medicamento inválido")
    
    med = db.query(Medication).filter(Medication.id == med_uuid).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    
    med.box_image = data.get("box_image")
    db.commit()
    return {"status": "success", "message": "Imagem da caixa do remédio salva com sucesso"}
 
async def notify_responsible_async(medication_id: uuid.UUID):
    """Aciona responsável do cliente quando este não toma a medicação"""
    db = SessionLocal()
    try:
        med = db.query(Medication).filter(Medication.id == medication_id).first()
        if not med:
            print("⚠️ notify_responsible_async: Medicamento não encontrado")
            return
            
        user = db.query(User).filter(User.id == med.user_id).first()
        paciente_nome = user.full_name if user else "O paciente"
        
        responsibles = db.query(Responsible).filter(Responsible.user_id == med.user_id).all()
        
        from datetime import datetime, timezone, timedelta
        brasilia_tz = timezone(timedelta(hours=-3))
        now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(brasilia_tz)
        dia = now.strftime("%d/%m")
        horario = med.time.strftime('%H:%M') if med.time else now.strftime('%H:%M')
        
        # Mensagem formatada exatamente conforme o exemplo
        mensagem = f"⚠️ *CR$ HOME CARE AI - ALERTA*\n\nA {paciente_nome} não tomou o remédio *{med.name}* das {horario} de hoje dia {dia}."
        
        for resp in responsibles:
            whatsapp_habilitado = resp.notify_whatsapp if resp.notify_whatsapp is not None else True
            ligacao_habilitada = resp.notify_call if resp.notify_call is not None else False
            
            if whatsapp_habilitado:
                print(f"📱 Enviando WhatsApp para {resp.name} ({resp.phone}): {mensagem}")
                enviar_whatsapp_custom(resp.phone, mensagem)
                
            if ligacao_habilitada:
                print(f"📞 [MOCK CALL] Fazendo ligação telefônica para {resp.name} ({resp.phone}): {mensagem}")
                
    except Exception as e:
        print(f"❌ Erro em notify_responsible_async: {e}")
    finally:
        db.close()
    # TODO: Integrar com API de mensagem aqui
    # await whatsapp_api.send(f"⚠️ Alerta: {medication.name} não foi tomado.")

# =========================================================
# 📅 CRUD CONSULTAS
# =========================================================

@app.get("/api/cliente/{user_id}/appointments")
async def get_client_appointments(user_id: str, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    cutoff_date = date.today() - timedelta(days=7)
    
    appointments = db.query(Appointment).filter(
        Appointment.user_id == user_uuid,
        Appointment.appointment_date >= cutoff_date
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    resultado = []
    for appt in appointments:
        resultado.append({
            "id": str(appt.id),
            "doctor_name": appt.doctor_name,
            "specialty": appt.specialty,
            "appointment_date": appt.appointment_date.isoformat(),
            "appointment_time": appt.appointment_time.strftime('%H:%M') if appt.appointment_time else None,
            "notes": appt.notes,
            "status": appt.status
        })
    
    return resultado

@app.post("/api/cliente/{user_id}/appointments", status_code=status.HTTP_201_CREATED)
async def create_appointment(user_id: str, appt: AppointmentCreate, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    nova_appt = Appointment(
        user_id=user_uuid,
        doctor_name=appt.doctor_name,
        specialty=appt.specialty,
        appointment_date=appt.appointment_date,
        appointment_time=appt.appointment_time,
        notes=appt.notes,
        status="scheduled"
    )
    
    db.add(nova_appt)
    db.commit()
    db.refresh(nova_appt)
    
    return {"status": "sucesso", "id": str(nova_appt.id)}

# =========================================================
# 👥 CRUD RESPONSÁVEIS
# =========================================================

@app.get("/api/cliente/{user_id}/responsibles", response_model=List[ClienteResponsibleResponse])
async def get_client_responsibles(user_id: str, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    responsibles = db.query(Responsible).filter(Responsible.user_id == user_uuid).all()
    
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "relationship": r.relationship,
            "phone": r.phone,
            "notify_sms": r.notify_sms,
            "notify_whatsapp": r.notify_whatsapp if r.notify_whatsapp is not None else True,
            "notify_call": r.notify_call if r.notify_call is not None else False
        } for r in responsibles
    ]

@app.post("/api/cliente/{user_id}/responsibles", status_code=status.HTTP_201_CREATED)
async def create_responsible(user_id: str, resp: ResponsibleCreate, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    novo_resp = Responsible(
        user_id=user_uuid,
        name=resp.name,
        relationship=resp.relationship,
        phone=resp.phone,
        notify_sms=resp.notify_sms,
        notify_email=resp.notify_email,
        notify_whatsapp=resp.notify_whatsapp if resp.notify_whatsapp is not None else True,
        notify_call=resp.notify_call if resp.notify_call is not None else False
    )
    
    db.add(novo_resp)
    db.commit()
    db.refresh(novo_resp)
    
    return {"status": "sucesso", "id": str(novo_resp.id)}

# =========================================================
# 📞 CRUD CONTATOS DE EMERGÊNCIA (APENAS 1x)
# =========================================================

@app.get("/api/cliente/{user_id}/emergency-contacts")
async def get_emergency_contacts(user_id: str, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    contacts = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == user_uuid
    ).order_by(EmergencyContact.name).all()
    
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "type": c.contact_type,
            "phone": c.phone,
            "email": c.email,
            "notes": c.notes
        } for c in contacts
    ]

@app.post("/api/cliente/{user_id}/emergency-contacts", status_code=201)
async def create_emergency_contact(user_id: str, contact: EmergencyContactCreate, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    new_contact = EmergencyContact(
        user_id=user_uuid,
        name=contact.name,
        contact_type=contact.type,  # ✅ Mapeia 'type' do frontend para 'contact_type' do banco
        phone=contact.phone,
        email=contact.email,
        notes=contact.notes
    )
    
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    
    return {"status": "sucesso", "id": str(new_contact.id)}


# =========================================================
# 👨‍💼 DASHBOARD ADMIN
# =========================================================

@app.get("/api/admin/clientes")
async def listar_clientes_admin(db: Session = Depends(get_db)):
    from datetime import date
    
    clientes = db.query(User).filter(
        User.is_active == True,
        User.email != 'admin@homecare.com'
    ).all()
    
    resultado = []
    today = date.today()
    
    for cliente in clientes:
        meds_count = db.query(Medication).filter(
            Medication.user_id == cliente.id,
            Medication.is_active == True
        ).count()
        
        resp_count = db.query(Responsible).filter(
            Responsible.user_id == cliente.id
        ).count()
        
        consultas_count = db.query(Appointment).filter(
            Appointment.user_id == cliente.id,
            Appointment.appointment_date >= today
        ).count()
        
        tem_agendamento = consultas_count > 0
        contatos_count = 0  # Por enquanto 0
        
        resultado.append({
            "id": str(cliente.id),
            "full_name": cliente.full_name,
            "email": cliente.email,
            "phone": cliente.phone,
            "medications_count": meds_count,
            "consultas_count": consultas_count,
            "responsibles_count": resp_count,
            "contatos_count": contatos_count,
            "has_appointment": tem_agendamento
        })
    
    return {"clientes": resultado}

# =========================================================
# 📋 ROTAS ADMIN
# =========================================================

@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
        
    if user.phone:
        existing_phone = db.query(User).filter(User.phone == user.phone).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Telefone já cadastrado por outro usuário")
    
    password_hash = sha256(user.password.encode()).hexdigest()
    db_user = User(full_name=user.full_name, email=user.email, phone=user.phone, password_hash=password_hash)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@app.post("/api/create-admin")
async def create_admin(db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == "admin@homecare.com").first()
    if existing:
        return {"message": "Admin já existe", "id": str(existing.id)}
    
    admin = User(full_name="Administrador", email="admin@homecare.com", phone="(00) 00000-0000", password_hash=sha256("admin123".encode()).hexdigest())
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {"message": "Admin criado com sucesso!", "id": str(admin.id)}

# =========================================================
# 🔧 ROTAS DE EDIÇÃO E EXCLUSÃO (ADICIONADAS)
# =========================================================

# --- 📅 APPOINTMENTS - EDITAR E EXCLUIR ---

@app.put("/api/appointments/{appt_id}")
async def update_appointment(
    appt_id: str, 
    appt: AppointmentCreate, 
    db: Session = Depends(get_db)
):
    """Editar uma consulta existente"""
    try:
        appt_uuid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    appointment = db.query(Appointment).filter(Appointment.id == appt_uuid).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    
    # Atualizar campos
    appointment.doctor_name = appt.doctor_name
    appointment.specialty = appt.specialty
    appointment.appointment_date = appt.appointment_date
    appointment.appointment_time = appt.appointment_time
    appointment.notes = appt.notes
    
    db.commit()
    db.refresh(appointment)
    
    return {"status": "sucesso", "mensagem": "Consulta atualizada"}


@app.delete("/api/appointments/{appt_id}")
async def delete_appointment(appt_id: str, db: Session = Depends(get_db)):
    """Excluir uma consulta"""
    try:
        appt_uuid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    appointment = db.query(Appointment).filter(Appointment.id == appt_uuid).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    
    db.delete(appointment)
    db.commit()
    
    return {"status": "sucesso", "mensagem": "Consulta excluída"}


@app.post("/api/appointments/{appt_id}/confirm")
async def confirm_appointment(appt_id: str, db: Session = Depends(get_db)):
    """Confirmar uma consulta"""
    try:
        appt_uuid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    appointment = db.query(Appointment).filter(Appointment.id == appt_uuid).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    
    appointment.status = "confirmed"
    db.commit()
    
    return {"status": "sucesso", "mensagem": "Consulta confirmada"}


@app.post("/api/appointments/{appt_id}/cancel")
async def cancel_appointment(appt_id: str, db: Session = Depends(get_db)):
    """Cancelar uma consulta"""
    try:
        appt_uuid = uuid.UUID(appt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    appointment = db.query(Appointment).filter(Appointment.id == appt_uuid).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    
    appointment.status = "cancelled"
    db.commit()
    
    return {"status": "sucesso", "mensagem": "Consulta cancelada"}


# --- 💊 MEDICATIONS - EDITAR E EXCLUIR ---

@app.put("/api/medications/{med_id}")
async def update_medication(
    med_id: str, 
    med: MedicationCreate, 
    db: Session = Depends(get_db)
):
    """Editar um medicamento existente"""
    try:
        med_uuid = uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    medication = db.query(Medication).filter(Medication.id == med_uuid).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medicação não encontrada")
    
    # Atualizar campos
    medication.name = med.name
    medication.dosage = med.dosage
    medication.time = med.time
    medication.days_of_week = med.days_of_week
    
    start_dt = medication.created_at.date() if medication.created_at else date.today()
    if getattr(med, 'start_date', None):
        try:
            start_dt = datetime.strptime(med.start_date, "%Y-%m-%d").date()
        except ValueError:
            pass
            
    actual_start = get_actual_start_date(start_dt, med.days_of_week)
    medication.created_at = datetime.combine(actual_start, time(0, 0, 0))
    
    if hasattr(med, 'is_continuous') and med.is_continuous:
        medication.end_date = None
        medication.is_continuous = True
    elif hasattr(med, 'duration_days') and med.duration_days is not None and med.duration_days > 0:
        medication.end_date = (actual_start + timedelta(days=med.duration_days - 1)).strftime("%Y-%m-%d")
        medication.is_continuous = False
    else:
        medication.end_date = None
        medication.is_continuous = False
    
    # Ao editar, resetar o status para garantir que o alarme toque caso o horário mude
    medication.taken_status = "pending"
    medication.last_taken_date = None
    medication.reminder_count = 0
    medication.responsible_notified = False
    
    db.commit()
    db.refresh(medication)
    
    return {"status": "sucesso", "mensagem": "Medicação atualizada"}


# ==================== ROTA: ALERTA DE REVISÃO (REGRA 5c) ====================
@app.get("/api/medications/review-needed")
async def get_review_needed_medications(user_id: str = None, db: Session = Depends(get_db)):
    """
    Retorna medicamentos contínuos que já passaram do prazo de revisão.
    
    Parâmetro opcional:
        user_id: filtra por usuário específico
    
    Retorna:
        Lista de medicamentos com is_review_needed=true e review_date
    """
    query = db.query(Medication).filter(
        Medication.is_continuous == True,
        Medication.is_active == True,
        Medication.start_date != None
    )
    
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            query = query.filter(Medication.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    all_continuous = query.all()
    
    resultado = []
    for med in all_continuous:
        try:
            start_dt = datetime.strptime(med.start_date, "%Y-%m-%d").date()
            needs_review = is_review_needed(start_dt, med.continuous_months)
            review_dt = get_review_date(start_dt, med.continuous_months)
            
            if needs_review:
                resultado.append({
                    "id": str(med.id),
                    "user_id": str(med.user_id),
                    "name": med.name,
                    "dosage": med.dosage,
                    "start_date": med.start_date,
                    "continuous_months": med.continuous_months,
                    "review_date": review_dt.isoformat(),
                    "days_overdue": (date.today() - review_dt).days,
                    "is_review_needed": True,
                })
        except (ValueError, TypeError):
            continue  # Pula registros com data inválida
    
    return resultado


@app.delete("/api/medications/{med_id}")
async def delete_medication(med_id: str, scope: str = "all", db: Session = Depends(get_db)):
    """
    Excluir medicamento com opções de escopo (Requisito 7):
    - scope=today: Cancela apenas schedules de hoje
    - scope=future: Cancela schedules de hoje em diante, preserva passado
    - scope=all: Soft delete total (comportamento padrão)
    """
    try:
        med_uuid = uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    medication = db.query(Medication).filter(Medication.id == med_uuid).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medicação não encontrada")
    
    today = date.today()
    
    if scope == "today":
        # Cancela apenas os schedules de HOJE
        updated = db.query(MedicationSchedule).filter(
            MedicationSchedule.medication_id == med_uuid,
            MedicationSchedule.scheduled_date == today,
            MedicationSchedule.status == "pending"
        ).update({"status": "cancelled"})
        db.commit()
        return {
            "status": "sucesso",
            "mensagem": f"{updated} dose(s) de hoje cancelada(s). Próximas doses mantidas.",
            "scope": "today",
            "cancelados": updated,
        }
    
    elif scope == "future":
        # Cancela schedules de hoje em diante, preserva os passados
        updated = db.query(MedicationSchedule).filter(
            MedicationSchedule.medication_id == med_uuid,
            MedicationSchedule.scheduled_date >= today,
            MedicationSchedule.status == "pending"
        ).update({"status": "cancelled"})
        
        # Atualiza end_date do medicamento para ontem
        medication.end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        db.commit()
        
        # Conta quantos schedules passados permanecem
        past_count = db.query(MedicationSchedule).filter(
            MedicationSchedule.medication_id == med_uuid,
            MedicationSchedule.scheduled_date < today,
        ).count()
        
        return {
            "status": "sucesso",
            "mensagem": f"{updated} dose(s) futuras canceladas. {past_count} registros passados preservados no histórico.",
            "scope": "future",
            "cancelados": updated,
            "historico_preservado": past_count,
        }
    
    else:  # scope == "all"
        # Soft delete: marca medicamento como inativo
        medication.is_active = False
        
        # Cancela todos os schedules pendentes
        db.query(MedicationSchedule).filter(
            MedicationSchedule.medication_id == med_uuid,
            MedicationSchedule.status == "pending"
        ).update({"status": "cancelled"})
        
        db.commit()
        
        return {
            "status": "sucesso",
            "mensagem": "Medicação excluída completamente.",
            "scope": "all",
        }


# --- 👥 RESPONSIBLES - EDITAR E EXCLUIR ---

@app.put("/api/cliente/{user_id}/responsibles/{resp_id}")
async def update_responsible(
    user_id: str,
    resp_id: str,
    resp: ResponsibleCreate,
    db: Session = Depends(get_db)
):
    """Editar um responsável existente"""
    try:
        user_uuid = uuid.UUID(user_id)
        resp_uuid = uuid.UUID(resp_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    responsible = db.query(Responsible).filter(
        Responsible.id == resp_uuid,
        Responsible.user_id == user_uuid
    ).first()
    
    if not responsible:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    
    # Atualizar campos
    responsible.name = resp.name
    responsible.relationship = resp.relationship
    responsible.phone = resp.phone
    responsible.notify_sms = resp.notify_sms
    responsible.notify_email = resp.notify_email
    responsible.notify_whatsapp = resp.notify_whatsapp if resp.notify_whatsapp is not None else True
    responsible.notify_call = resp.notify_call if resp.notify_call is not None else False
    
    db.commit()
    db.refresh(responsible)
    
    return {"status": "sucesso", "mensagem": "Responsável atualizado"}


@app.delete("/api/cliente/{user_id}/responsibles/{resp_id}")
async def delete_responsible(user_id: str, resp_id: str, db: Session = Depends(get_db)):
    """Excluir um responsável"""
    try:
        user_uuid = uuid.UUID(user_id)
        resp_uuid = uuid.UUID(resp_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    responsible = db.query(Responsible).filter(
        Responsible.id == resp_uuid,
        Responsible.user_id == user_uuid
    ).first()
    
    if not responsible:
        raise HTTPException(status_code=404, detail="Responsável não encontrado")
    
    db.delete(responsible)
    db.commit()
    
    return {"status": "sucesso", "mensagem": "Responsável excluído"}


# --- 📞 EMERGENCY CONTACTS - EDITAR E EXCLUIR ---

@app.put("/api/emergency-contacts/{contact_id}")
async def update_emergency_contact(
    contact_id: str,
    contact: EmergencyContactCreate,
    db: Session = Depends(get_db)
):
    """Editar um contato de emergência"""
    try:
        contact_uuid = uuid.UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    emergency_contact = db.query(EmergencyContact).filter(
        EmergencyContact.id == contact_uuid
    ).first()
    
    if not emergency_contact:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    
    # Atualizar campos (mapear 'type' para 'contact_type')
    emergency_contact.name = contact.name
    emergency_contact.contact_type = contact.type
    emergency_contact.phone = contact.phone
    emergency_contact.email = contact.email
    emergency_contact.notes = contact.notes
    
    db.commit()
    db.refresh(emergency_contact)
    
    return {"status": "sucesso", "mensagem": "Contato atualizado"}


@app.delete("/api/emergency-contacts/{contact_id}")
async def delete_emergency_contact(contact_id: str, db: Session = Depends(get_db)):
    """Excluir um contato de emergência"""
    try:
        contact_uuid = uuid.UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    emergency_contact = db.query(EmergencyContact).filter(
        EmergencyContact.id == contact_uuid
    ).first()
    
    if not emergency_contact:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    
    db.delete(emergency_contact)
    db.commit()
    
    return {"status": "sucesso", "mensagem": "Contato excluído"}

# ===== PWA ROUTES =====


@app.get("/manifest.json")
async def get_manifest():
    return FileResponse("manifest.json", media_type="application/manifest+json")
# ==========================================================
#  INTEGRAÇÃO WHATSAPP BUSINESS API (META)
# ==========================================================
import os
import json
import requests
import re

# Função auxiliar para enviar WhatsApp
def enviar_whatsapp(telefone: str, nome_remedio: str, dosagem: str) -> bool:
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    
    if not token or not phone_id:
        print("⚠️ WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID ausentes no .env do Vercel!")
        return False
        
    if not telefone:
        return False
        
    # 1. Normalização do Telefone Brasileiro
    # Remove qualquer caractere que não seja número
    nums = re.sub(r'\D', '', telefone)
    
    # Se for um número brasileiro local (ex: 61993683464), adiciona o DDI 55
    if len(nums) == 10 or len(nums) == 11:
        nums = "55" + nums
        
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. Monta a Mensagem
    from datetime import timezone, timedelta
    hora_atual = datetime.now(timezone(timedelta(hours=-3))).strftime("%H:%M")
    
    data = {
        "messaging_product": "whatsapp",
        "to": nums,
        "type": "text",
        "text": {
            "body": f"💊 *CR$ HOME CARE AI*\n\nOlá! São {hora_atual}.\nEstá na hora do medicamento:\n\n👉 *{nome_remedio}*\n⚖️ Dosagem: {dosagem}\n\nCuide-se!"
        }
    }
    
    # 3. Dispara a requisição HTTP para a Meta
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            print(f"✅ WhatsApp enviado com sucesso para {nums}")
            return True
        else:
            print(f"❌ Erro da API WhatsApp para {nums}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Falha de conexão WhatsApp: {e}")
        return False

# Função auxiliar para enviar mensagem customizada pelo WhatsApp
def enviar_whatsapp_custom(telefone: str, texto: str) -> bool:
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    
    if not token or not phone_id:
        print("⚠️ WHATSAPP_TOKEN ou WHATSAPP_PHONE_ID ausentes no .env!")
        return False
        
    if not telefone:
        return False
        
    nums = re.sub(r'\D', '', telefone)
    if len(nums) == 10 or len(nums) == 11:
        nums = "55" + nums
        
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": nums,
        "type": "text",
        "text": {
            "body": texto
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            print(f"✅ WhatsApp Custom enviado com sucesso para {nums}")
            return True
        else:
            print(f"❌ Erro da API WhatsApp Custom para {nums}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Falha de conexão WhatsApp Custom: {e}")
        return False

# Função auxiliar para enviar Web Push
def enviar_web_push(subscription_info: dict, message_text: str) -> bool:
    private_key = os.getenv("VAPID_PRIVATE_KEY")
    if not private_key:
        print("⚠️ VAPID_PRIVATE_KEY ausente no .env!")
        return False
        
    vapid_claims = {
        "sub": "mailto:suporte@homecare.com.br"
    }
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=message_text,
            vapid_private_key=private_key,
            vapid_claims=vapid_claims
        )
        return True
    except WebPushException as ex:
        print(f"❌ Erro ao enviar Web Push: {ex}")
        return False
    except Exception as e:
        print(f"❌ Falha genérica Web Push: {e}")
        return False

# Rota ativa para salvar a inscrição de Web Push
@app.post("/api/push/subscribe")
async def subscribe_push(req: PushSubscriptionCreate, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(req.user_id)
        # Verifica se já existe
        sub = db.query(PushSubscription).filter(PushSubscription.endpoint == req.endpoint).first()
        if not sub:
            sub = PushSubscription(
                user_id=user_uuid,
                endpoint=req.endpoint,
                keys=req.keys
            )
            db.add(sub)
        else:
            sub.user_id = user_uuid
            sub.keys = req.keys
        db.commit()
        return {"status": "success", "message": "Inscrição de Web Push registrada com sucesso!"}
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 2. Endpoint para TESTE RÁPIDO DO WHATSAPP (Dispara manualmente)
@app.api_route("/api/teste-push", methods=["GET", "POST"])
async def test_whatsapp(db: Session = Depends(get_db)):
    # Pega o primeiro usuário apenas para teste
    user = db.query(User).filter(User.phone.isnot(None)).first()
    if not user:
        return {"msg": "Nenhum usuário com telefone cadastrado no banco."}
        
    enviado = enviar_whatsapp(user.phone, "Teste de Sistema", "1 Gota")
    
    if enviado:
        return {"msg": f"WhatsApp de teste enviado para {user.phone} com sucesso!"}
    else:
        return {"msg": "Falha ao enviar WhatsApp. Verifique os logs do Vercel e as variáveis de ambiente."}

# =========================================================
# 3. AGENDADOR AUTOMÁTICO (O "Cérebro" que roda a cada minuto)
# =========================================================
@app.get("/api/check-reminders")
async def check_reminders(db: Session = Depends(get_db)):
    """
    Verifica medicamentos que devem ser tomados AGORA (horário de Brasília)
    e envia mensagens no WhatsApp para os usuários.
    """
    from datetime import timezone, timedelta
    
    print("🔔 [CRON] INICIANDO VERIFICAÇÃO DE MEDICAMENTOS (WHATSAPP)...")
    
    try:
        brasilia_tz = timezone(timedelta(hours=-3))
        now = datetime.now(brasilia_tz)
        current_time = now.strftime("%H:%M")
        
        print(f"⏰ [CRON] Horário em Brasília: {current_time}")
        
        # Busca medicamentos
        meds_due = db.query(Medication).filter(
            Medication.time == current_time,
            Medication.is_active == True
        ).all()
        
        if not meds_due:
            print(f"ℹ️ Nenhum medicamento agendado para {current_time}")
            return {"status": "ok", "msg": "Nenhum remédio neste horário", "hora_brasilia": current_time}
            
        # Para cada medicamento, busca o usuário dono dele, manda WhatsApp e Web Push
        sent_count = 0
        failed_count = 0
        push_sent_count = 0
        
        for med in meds_due:
            user = db.query(User).filter(User.id == med.user_id).first()
            if user:
                # 1. Envia WhatsApp
                if user.phone:
                    print(f"📤 Enviando WhatsApp para {user.full_name} ({user.phone}) - Remédio: {med.name}")
                    sucesso = enviar_whatsapp(user.phone, med.name, med.dosage)
                    if sucesso:
                        sent_count += 1
                    else:
                        failed_count += 1
                else:
                    print(f"⚠️ Usuário {user.full_name} sem telefone para o medicamento {med.name}")
                    failed_count += 1
                
                # 2. Envia Web Push
                subs = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
                for sub in subs:
                    sub_info = {
                        "endpoint": sub.endpoint,
                        "keys": sub.keys
                    }
                    payload = json.dumps({
                        "title": "💊 Hora do Medicamento!",
                        "body": f"Olá {user.full_name}, está na hora de tomar seu remédio {med.name} ({med.dosage}) agendado para às {med.time}.",
                        "icon": "/static/icons/icon-192x192.png",
                        "badge": "/static/icons/icon-72x72.png",
                        "data": {
                            "url": "/dashboard-cliente",
                            "medication_id": str(med.id),
                            "medication_name": med.name,
                            "medication_dosage": med.dosage,
                            "medication_time": med.time
                        }
                    })
                    print(f"📤 Enviando Web Push para {user.full_name}...")
                    push_sucesso = enviar_web_push(sub_info, payload)
                    if push_sucesso:
                        push_sent_count += 1
            else:
                print(f"⚠️ Usuário não encontrado para o medicamento {med.name}")
                failed_count += 1
                
        resultado = {
            "status": "ok",
            "hora_brasilia": current_time,
            "medicamentos_encontrados": len(meds_due),
            "whatsapp_enviados": sent_count,
            "whatsapp_falhados": failed_count,
            "web_push_enviados": push_sent_count
        }
        
        print(f"📊 [CRON] RESULTADO FINAL: {resultado}")
        return resultado
        
    except Exception as e:
        print(f"💥 [CRON] ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "msg": str(e)}

# =========================================================
# 4. UPLOAD DE RECEITA MÉDICA (OCR)
# =========================================================



@app.post("/api/prescriptions/upload")
async def upload_prescription(file: UploadFile = File(...)):
    try:
        import base64
        import os
        # 1. Ler o arquivo enviado
        contents = await file.read()
        filename = file.filename.lower()
        mime_type = file.content_type or "image/jpeg"
        
        # Inferir mime type se indefinido
        if filename.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif filename.endswith('.png'):
            mime_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            mime_type = 'image/jpeg'
            
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise HTTPException(
                status_code=500, 
                detail="GEMINI_API_KEY nao configurada no servidor. Adicione a chave nas variaveis de ambiente."
            )
            
        # Converte para base64
        base64_data = base64.b64encode(contents).decode("utf-8")
        
        prompt = (
            "Voce e um assistente medico especialista em transcricao de receitas. "
            "Analise o documento enviado (imagem ou PDF) e extraia todos os medicamentos listados. "
            "Retorne as informacoes estruturadas estritamente no seguinte formato JSON:\n"
            "[\n"
            "  {\n"
            "    \"name\": \"Nome do Medicamento\",\n"
            "    \"dosage\": \"Dosagem e quantidade (ex: 500mg, 1 comprimido, 10 gotas)\",\n"
            "    \"frequency\": \"Frequencia de uso (ex: A cada 8 horas, 1 vez ao dia)\",\n"
            "    \"times\": [\"08:00\", \"16:00\", \"00:00\"],\n"
            "    \"duration_days\": 7\n"
            "  }\n"
            "]\n\n"
            "Instrucoes:\n"
            "1. 'times': Lista de horarios sugeridos HH:MM baseados na frequencia da receita. Se a receita indicar horarios especificos (ex: tomar as 08h e as 20h), use-os. Caso contrario, sugira horarios padrao (ex: a cada 12h use ['08:00', '20:00']).\n"
            "2. 'duration_days': Quantidade de dias do tratamento (inteiro). Se nao mencionado, use 7 por padrao.\n"
            "3. Retorne APENAS o array JSON. Nao inclua markdown (como ```json) ou qualquer outro texto explicativo."
        )
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                               "mimeType": mime_type,
                               "data": base64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        # Lista de modelos candidatas para fallback
        candidate_models = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.0-flash"]
        response = None
        errors = []
        chosen_model = ""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                headers = {"Content-Type": "application/json"}
                print(f"📡 Tentando enviar receita para o Gemini via modelo {model} ({mime_type})...")
                try:
                    r = await client.post(url, headers=headers, json=payload)
                    if r.status_code == 200:
                        response = r
                        chosen_model = model
                        print(f"✅ Sucesso com o modelo {model}!")
                        break
                    else:
                        err_msg = f"Modelo {model} retornou status {r.status_code}: {r.text[:300]}"
                        errors.append(err_msg)
                        print(f"⚠️ {err_msg}")
                except Exception as ex:
                    err_msg = f"Erro ao tentar modelo {model}: {str(ex)}"
                    errors.append(err_msg)
                    print(f"⚠️ {err_msg}")
        
        if not response:
            all_errors_str = " | ".join(errors)
            raise HTTPException(status_code=502, detail=f"Erro da API do Gemini (Todos os modelos falharam). Detalhes: {all_errors_str}")
            
        resp_json = response.json()
        
        try:
            generated_text = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"🤖 Resposta do Gemini ({chosen_model}):\n{generated_text}")
            
            if generated_text.startswith("```"):
                generated_text = re.sub(r"^```(?:json)?\n", "", generated_text)
                generated_text = re.sub(r"\n```$", "", generated_text)
                generated_text = generated_text.strip()
                
            medications = json.loads(generated_text)
        except Exception as parse_error:
            print(f"❌ Erro ao parsear JSON do Gemini: {parse_error}")
            raise HTTPException(status_code=500, detail="Erro ao parsear dados extraidos pelo Gemini.")
            
        return JSONResponse(content={
            "success": True,
            "medications": medications,
            "raw_text_preview": f"Extraido via Gemini ({chosen_model})",
            "message": f"✅ {len(medications)} medicamentos identificados com IA!"
        })
        
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        print(f"🔥 Erro no upload de receita: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cliente/{user_id}/ocr-allergies")
async def ocr_allergies(user_id: str, file: UploadFile = File(...)):
    try:
        import base64
        import os
        contents = await file.read()
        filename = file.filename.lower()
        mime_type = file.content_type or "image/jpeg"
        
        if filename.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif filename.endswith('.png'):
            mime_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            mime_type = 'image/jpeg'
            
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise HTTPException(
                status_code=500, 
                detail="GEMINI_API_KEY nao configurada no servidor."
            )
            
        base64_data = base64.b64encode(contents).decode("utf-8")
        
        prompt = (
            "Voce e um assistente medico especialista em analise de laudos e exames. "
            "Analise a imagem ou documento enviado, que contem informacoes sobre alergias do paciente. "
            "Extraia todas as alergias listadas (podem ser a medicamentos, alimentos, produtos quimicos ou substancias). "
            "Retorne a lista de alergias identificadas separadas por virgula em formato de texto simples. "
            "Exemplo: 'Dipirona, Penicilina, Corantes alimenticios, Lactose'. "
            "Se nao encontrar nenhuma alergia listada ou o documento nao for sobre isso, retorne 'Nenhuma alergia relatada'."
            "Retorne APENAS a lista no formato de texto simples, sem markdown ou explicacoes adicionais."
        )
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                               "mimeType": mime_type,
                               "data": base64_data
                            }
                        }
                    ]
                }
            ]
        }
        
        candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash"]
        response = None
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                headers = {"Content-Type": "application/json"}
                try:
                    r = await client.post(url, headers=headers, json=payload)
                    if r.status_code == 200:
                        response = r
                        break
                except Exception as ex:
                    print(f"⚠️ Erro ao tentar modelo {model} para alergias: {str(ex)}")
        
        if not response:
            raise HTTPException(status_code=502, detail="Erro da API do Gemini (falha na leitura de alergias).")
            
        generated_text = "Nenhuma alergia relatada"
        try:
            resp_json = response.json()
            candidates = resp_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    generated_text = parts[0].get("text", "").strip()
        except Exception as parse_ex:
            print(f"⚠️ Erro ao parsear resposta do Gemini para alergias: {parse_ex}")
            
        return JSONResponse(content={
            "success": True,
            "allergies": generated_text
        })
    except Exception as e:
        print(f"🔥 Erro no OCR de alergias: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cliente/{user_id}/upload-insurance-card")
async def upload_insurance_card(user_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        import base64
        import os
        
        user_uuid = uuid.UUID(user_id)
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
            
        contents = await file.read()
        filename = file.filename.lower()
        ext = os.path.splitext(filename)[1]
        
        # Salva o arquivo — /tmp/ na Vercel (read-only filesystem), static/uploads/ local
        if IS_VERCEL:
            upload_dir = "/tmp/uploads"
        else:
            upload_dir = "static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        unique_filename = f"card_{user_id}_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, unique_filename)
        
        with open(filepath, "wb") as f:
            f.write(contents)
            
        # Cria a URL publica — endpoint dedicado para compatibilidade Vercel
        card_url = f"/api/files/uploads/{unique_filename}"
        
        # Faz o OCR da carteirinha para tentar ler a operadora/convenio
        mime_type = file.content_type or "image/jpeg"
        if filename.endswith('.png'):
            mime_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif filename.endswith('.pdf'):
            mime_type = 'application/pdf'
            
        gemini_key = os.getenv("GEMINI_API_KEY")
        insurance_name = ""
        
        if gemini_key:
            base64_data = base64.b64encode(contents).decode("utf-8")
            prompt = (
                "Voce e um assistente administrativo de home care especialista em ler carteirinhas de planos de saude. "
                "Analise o arquivo enviado. Ele contem a frente ou verso de um cartao de convenio/plano de saude. "
                "Extraia o nome da operadora/empresa do plano de saude (ex: Unimed, Amil, SulAmerica, Bradesco, Cassi, Golden Cross, etc.). "
                "Se encontrar o numero da carteirinha ou matricula, extraia-o tambem e monte no seguinte padrao: 'Nome do Plano (Nº Numero)'. "
                "Retorne apenas essa informacao em formato de texto simples, sem markdown ou justificativas. "
                "Se nao conseguir ler nada plausivel, retorne apenas 'Convenio'."
            )
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                   "mimeType": mime_type,
                                   "data": base64_data
                                }
                            }
                        ]
                    }
                ]
            }
            
            candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            response = None
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for model in candidate_models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                    headers = {"Content-Type": "application/json"}
                    try:
                        r = await client.post(url, headers=headers, json=payload)
                        if r.status_code == 200:
                            response = r
                            break
                    except Exception as ex:
                        print(f"⚠️ Erro ao tentar modelo {model} para carteirinha: {str(ex)}")
            
            if response:
                try:
                    resp_json = response.json()
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            insurance_name = parts[0].get("text", "").strip()
                except Exception as parse_ex:
                    print(f"⚠️ Erro ao parsear resposta do Gemini para carteirinha: {parse_ex}")
                
        if not insurance_name:
            insurance_name = "Convenio"
            
        # Atualiza no banco
        user.health_insurance = insurance_name
        user.health_insurance_card = card_url
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "health_insurance": insurance_name,
            "health_insurance_card": card_url
        })
    except Exception as e:
        print(f"🔥 Erro no upload da carteirinha do convenio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ENDPOINT PARA SERVIR ARQUIVOS DE UPLOAD (compatível com Vercel /tmp) =====
@app.get("/api/files/uploads/{filename}")
async def serve_uploaded_file(filename: str):
    """Serve arquivos de upload — usa /tmp/ na Vercel, static/uploads/ local."""
    import os
    if IS_VERCEL:
        filepath = os.path.join("/tmp/uploads", filename)
    else:
        filepath = os.path.join("static/uploads", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    return FileResponse(filepath)

@app.post("/api/cliente/{user_id}/upload-identity-document")
async def upload_identity_document(user_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        import base64
        import os
        
        user_uuid = uuid.UUID(user_id)
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
            
        contents = await file.read()
        filename = file.filename.lower()
        ext = os.path.splitext(filename)[1]
        
        # Salva o arquivo — /tmp/ na Vercel (read-only filesystem), static/uploads/ local
        if IS_VERCEL:
            upload_dir = "/tmp/uploads"
        else:
            upload_dir = "static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        unique_filename = f"id_{user_id}_{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, unique_filename)
        
        with open(filepath, "wb") as f:
            f.write(contents)
            
        doc_url = f"/api/files/uploads/{unique_filename}"
        
        mime_type = file.content_type or "image/jpeg"
        if filename.endswith('.png'):
            mime_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif filename.endswith('.pdf'):
            mime_type = 'application/pdf'
            
        gemini_key = os.getenv("GEMINI_API_KEY")
        doc_info = ""
        
        if gemini_key:
            base64_data = base64.b64encode(contents).decode("utf-8")
            prompt = (
                "Voce e um assistente administrativo especialista em ler documentos de identificacao. "
                "Analise o arquivo enviado (pode ser imagem ou PDF). Ele contem um documento como RG, CPF, CNH ou outro. "
                "Extraia o tipo de documento e o seu numero principal (por exemplo, se for CPF, extraia 'CPF: 123.456.789-00'. Se for RG, 'RG: 12.345.678-9'). "
                "Retorne apenas essa informacao em formato de texto simples, bem curto (ex: 'CPF: 123.456.789-00' ou 'RG: 12.345.678-9'). "
                "Retorne apenas o texto cru, sem explicacoes, sem markdown."
            )
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                   "mimeType": mime_type,
                                   "data": base64_data
                                }
                            }
                        ]
                    }
                ]
            }
            
            candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            response = None
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for model in candidate_models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                    headers = {"Content-Type": "application/json"}
                    try:
                        r = await client.post(url, headers=headers, json=payload)
                        if r.status_code == 200:
                            response = r
                            break
                    except Exception as ex:
                        print(f"⚠️ Erro ao tentar modelo {model} para documento: {str(ex)}")
            
            if response:
                try:
                    resp_json = response.json()
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            doc_info = parts[0].get("text", "").strip()
                except Exception as parse_ex:
                    print(f"⚠️ Erro ao parsear resposta do Gemini para documento: {parse_ex}")
                
        if not doc_info:
            doc_info = "Documento"
            
        user.identity_document = doc_info
        user.identity_document_file = doc_url
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "identity_document": doc_info,
            "identity_document_file": doc_url
        })
    except Exception as e:
        print(f"🔥 Erro no upload do documento de identificacao: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_assistant(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        user_id = req.user_id
        message = req.message
        history = req.history or []
        
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="ID de usuário inválido")
            
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
            
        medications = db.query(Medication).filter(
            Medication.user_id == user_uuid, 
            Medication.is_active == True
        ).all()
        
        # Busca schedules de hoje para informar ao Maximus
        from datetime import date
        today_date = date.today()
        today_schedules = db.query(MedicationSchedule).filter(
            MedicationSchedule.user_id == user_uuid,
            MedicationSchedule.scheduled_date == today_date
        ).all()
        
        schedules_by_med = {}
        for s in today_schedules:
            if s.medication_id not in schedules_by_med:
                schedules_by_med[s.medication_id] = []
            schedules_by_med[s.medication_id].append({
                "time": s.scheduled_time.strftime("%H:%M") if s.scheduled_time else "",
                "status": s.status,
                "confirmed_at": s.confirmed_at
            })
            
        # 1. Carrega a chave
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise HTTPException(
                status_code=500, 
                detail="GEMINI_API_KEY nao configurada no servidor."
            )
            
        # 2. Monta as instruções do sistema com contexto do paciente
        sys_instruction = (
            "Você é o 'Maximus', o assistente médico e de cuidado pessoal inteligente do sistema CR$ HOME CARE AI.\n"
            "Seu objetivo é ajudar o paciente ou seu cuidador respondendo perguntas sobre medicamentos, orientações de uso, saúde e bem-estar.\n"
            "Aja como um(a) cuidador(a) real, de forma extremamente humana, empática e carinhosa. "
            "Quando for consultado sobre o que tomar no dia ou o status dos remédios, e houver medicamentos que já foram tomados hoje (status 'Tomado'), informe isso com carinho e parabenize o paciente por se cuidar tão bem.\n\n"
            "CONTEXTO DO PACIENTE:\n"
            f"- Nome: {user.full_name}\n"
            f"- Idade: {user.age or 'Não informada'} anos\n"
            f"- Documento de Identificação: {user.identity_document or 'Não informado'}\n"
            f"- Alergias conhecidas: {user.allergies or 'Nenhuma informada'}\n"
            f"- Condições médicas: {user.conditions or 'Nenhuma informada'}\n"
            f"- Tipo sanguíneo: {user.blood_type or 'Não informado'}\n"
            f"- Plano de saúde: {user.health_insurance or 'Não informado'}\n\n"
            "MEDICAMENTOS ATIVOS CADASTRADOS:\n"
        )
        if medications:
            for med in medications:
                time_str = med.time.strftime('%H:%M') if med.time else 'Não informado'
                sys_instruction += f"- {med.name}: Dosagem '{med.dosage}', Horário '{time_str}', Contínuo? {'Sim' if med.is_continuous else 'Não'}, Término? {med.end_date or 'Uso contínuo'}"
                
                # Anexa o status das doses de hoje
                med_scheds = schedules_by_med.get(med.id, [])
                if med_scheds:
                    scheds_desc = []
                    for ms in med_scheds:
                        status_pt = "Pendente"
                        if ms["status"] == "taken":
                            status_pt = f"Tomado (confirmado às {ms['confirmed_at'].strftime('%H:%M') if ms['confirmed_at'] else ''})"
                        elif ms["status"] == "skipped":
                            status_pt = "Pulado"
                        elif ms["status"] == "cancelled":
                            status_pt = "Cancelado"
                        scheds_desc.append(f"{ms['time']} ({status_pt})")
                    sys_instruction += f" | Status das doses de hoje: {', '.join(scheds_desc)}"
                sys_instruction += "\n"
        else:
            sys_instruction += "- Nenhum medicamento ativo cadastrado no momento.\n"
            
        sys_instruction += (
            "\nREGRAS DE COMPORTAMENTO:\n"
            "1. Aja de forma muito atenciosa, empática, acolhedora e fale sempre em português do Brasil.\n"
            "2. Se o paciente perguntar sobre os remédios dele do dia, faça questão de mencionar carinhosamente quais ele já tomou hoje (por exemplo: 'Que maravilha, você já tomou o seu [Nome] das [Horário] hoje! Estão restando apenas os seguintes...').\n"
            "3. Dê respostas curtas, práticas e objetivas. Evite textos longos ou excessivamente técnicos.\n"
            "4. Use formatação em Markdown (negrito, listas, etc.) para facilitar a leitura.\n"
            "5. IMPORTANTE: Você é um assistente de IA. Sempre recomende que o paciente consulte o médico ou responsável em caso de dúvidas graves, dor intensa ou reações adversas incomuns.\n"
            "6. Use o histórico de conversas fornecido para manter o contexto."
        )
        
        # 3. Prepara contents para a API (histórico + mensagem atual)
        contents = []
        for h in history:
            # Garante que está no formato correto para a API
            if "role" in h and "parts" in h:
                parts = []
                for p in h["parts"]:
                    if isinstance(p, dict) and "text" in p:
                        parts.append(p)
                    elif isinstance(p, str):
                        parts.append({"text": p})
                contents.append({"role": h["role"], "parts": parts})
                
        # Adiciona a mensagem atual do usuário
        contents.append({"role": "user", "parts": [{"text": message}]})
        
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [
                    {"text": sys_instruction}
                ]
            }
        }
        
        candidate_models = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.0-flash"]
        response = None
        errors = []
        chosen_model = ""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                headers = {"Content-Type": "application/json"}
                try:
                    r = await client.post(url, headers=headers, json=payload)
                    if r.status_code == 200:
                        response = r
                        chosen_model = model
                        break
                    else:
                        errors.append(f"{model}: {r.status_code} - {r.text[:200]}")
                except Exception as ex:
                    errors.append(f"{model}: {str(ex)}")
                    
        if not response:
            all_errors_str = " | ".join(errors)
            raise HTTPException(status_code=502, detail=f"Erro da API do Gemini (Todos os modelos falharam). Detalhes: {all_errors_str}")
            
        resp_json = response.json()
        
        try:
            generated_text = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as parse_error:
            raise HTTPException(status_code=500, detail="Erro ao parsear resposta do Gemini.")
            
        return JSONResponse(content={
            "success": True,
            "response": generated_text,
            "model": chosen_model
        })
        
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        contact = req.contact.strip()
        user = db.query(User).filter(
            or_(
                User.email == contact,
                User.phone == contact,
                User.full_name.ilike(f"%{contact}%")
            )
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
            
        temp_pass = "redefinida123"
        user.password_hash = sha256(temp_pass.encode()).hexdigest()
        db.commit()
        
        return {
            "status": "sucesso",
            "detail": f"Senha do usuário {user.full_name} redefinida temporariamente para: {temp_pass}"
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Função auxiliar de parsing para extrair medicamentos do texto
def parse_medications_from_text(text: str) -> list:
    medications = []
    
    # Regex para encontrar padrões de medicamentos em receitas
    # Ex: "1) AMOXICILINA 500MG ... TOMAR 1CP ... POR 7 DIAS"
    pattern = r'(\d+\))\s*([A-ZÁ-Ú\s]+?)\s+(\d+\s*MG|G|MCG|ML|UI|CP|COMPRIMIDO|CÁPSULA).*?(?:TOMAR|USAR|APLICAR).*?(?:(\d+)\s*(?:CP|COMPRIMIDO|CÁPSULA|ML|GOTA|SERINGA))?.*?(?:(\d+)\s*(?:DIAS|SEMANAS|MESES))?'
    
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        med_name = match.group(2).strip().title()
        dosage = match.group(3).upper() if match.group(3) else "Dosagem não identificada"
        quantity = match.group(4) if match.group(4) else "1"
        duration = int(match.group(5)) if match.group(5) else 7
        
        medications.append({
            "name": med_name,
            "dosage": f"{quantity} {dosage}",
            "frequency": "Conforme prescrição",
            "times": ["08:00"],  # Sugestão padrão
            "duration_days": duration
        })
    
    return medications

from fastapi import HTTPException
# =========================================================
# Endpoint para confirmar tomada do 
# =========================================================
# =========================================================
# Função para notificar responsável
# (substituída por notify_responsible_async)
    
# ============================================
# 🚀 CONFIGURAÇÃO PARA VERCEL
# ============================================
import os

# Permitir CORS para produção
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "https://projeto-home-care.vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handler para Vercel serverless
if os.getenv("VERCEL"):
    @app.get("/")
    async def root():
        return {
            "status": "ok",
            "message": "CR$ HOME CARE API - Running on Vercel",
            "docs": "/docs"
        }    

async def enviar_sms_lembrete(telefone: str, medication):
    """Envia SMS/WhatsApp via Twilio ou Z-API"""
    
    # Opção A: Twilio (internacional)
    from twilio.rest import Client
    
    account_sid = os.getenv('TWILIO_SID')
    auth_token = os.getenv('TWILIO_TOKEN')
    client = Client(account_sid, auth_token)
    
    mensagem = (
        f"⏰ LEMBRETE DE MEDICAMENTO\n\n"
        f"💊 {medication.name}\n"
        f"📋 {medication.dosage}\n"
        f"⏰ Horário: {medication.time}\n\n"
        f"Por favor, tome seu medicamento!"
    )
    
    try:
        # SMS
        message = client.messages.create(
            body=mensagem,
            from_='+1234567890',  # Seu número Twilio
            to=f'+55{telefone}'
        )
        print(f"✅ SMS enviado: {message.sid}")
    except Exception as e:
        print(f"❌ Erro ao enviar SMS: {e}")

async def notificar_responsavel_se_nao_tomou(medication_id):
    """Verifica se medicamento foi tomado, senão notifica responsável"""
    from sqlalchemy.orm import Session
    from models import Medication, User, Responsible
    
    db = SessionLocal()
    med = db.query(Medication).filter(Medication.id == medication_id).first()
    
    if med and med.taken_status == 'pending':
        # Buscar responsáveis
        responsives = db.query(Responsible).filter(
            Responsible.user_id == med.user_id
        ).all()
        
        for resp in responsives:
            await enviar_sms_lembrete(resp.phone, med)
            # Ou WhatsApp
            await enviar_whatsapp_alerta(resp.phone, med)
    
    db.close()
# app.py - Adicionar no final

# ===== AGENDADOR DE MEDICAMENTOS (VERSÃO SÍNCRONA) =====
from apscheduler.schedulers.background import BackgroundScheduler

def verificar_medicamentos_sincrono():
    """Versão síncrona para APScheduler funcionar corretamente"""
    from sqlalchemy.orm import Session
    
    db = SessionLocal()
    try:
        agora = datetime.now()
        hora_atual = agora.strftime("%H:%M")
        
        print(f"🔔 [SCHEDULER] Verificando medicamentos para {hora_atual}")
        
        # Buscar medicamentos do horário atual
        meds = db.query(Medication).filter(
            Medication.time == hora_atual,
            Medication.is_active == True,
            Medication.taken_status == 'pending'
        ).all()
        
        for med in meds:
            user = db.query(User).filter(User.id == med.user_id).first()
            
            if user and user.phone:
                print(f"📱 Enviando WhatsApp para {user.full_name} ({user.phone})")
                # Chama função síncrona de envio
                enviar_whatsapp(user.phone, med.name, med.dosage)
        
        print(f"✅ [SCHEDULER] Verificação concluída. {len(meds)} medicamentos verificados.")
        
    except Exception as e:
        print(f"❌ Erro no scheduler: {e}")
    finally:
        db.close()

# Iniciar scheduler apenas localmente (evita erros em serverless Vercel)
if not IS_VERCEL:
    scheduler = BackgroundScheduler()
    scheduler.add_job(verificar_medicamentos_sincrono, 'interval', minutes=1)
    scheduler.start()
    print("⏰ Scheduler iniciado - verificando medicamentos a cada minuto")

# ===== INICIALIZAÇÃO =====
if __name__ == "__main__":
    import uvicorn
    # Só roda localmente, não na Vercel
    if not IS_VERCEL:
        print(" 🚀  CR$ HOME CARE AI - Iniciando...")
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

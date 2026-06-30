# ===== versão 1.04 - 2026-06-02 ================================
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
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
import pytesseract
from PIL import Image
import io
import re
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = os.path.join(os.path.dirname(__file__), 'tessdata')
import pytesseract
from PIL import Image
import io


# ===== CONFIGURAÇÃO PARA VERCEL =====
IS_VERCEL = os.getenv('VERCEL', '0') == '1'
if IS_VERCEL:
    sys.path.append(os.getcwd())

# Carrega variáveis de ambiente ANTES de usar
load_dotenv()

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
    created_at = Column(DateTime, default=datetime.utcnow)
    end_date = Column(String(10), nullable=True)  # "YYYY-MM-DD" ou use Date
    
    # NOVAS COLUNAS DO FLUXO DE ESTADO
    taken_status = Column(String(20), default="pending")
    reminder_count = Column(Integer, default=0)
    responsible_notified = Column(Boolean, default=False)
    last_taken_date = Column(Date, nullable=True)

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

class MedicationCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    dosage: str
    time: str
    days_of_week: List[int] = [0,1,2,3,4,5,6]
    is_continuous: bool = False
    duration_days: Optional[int] = None
    end_date: Optional[str] = None

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
    last_taken_date: Optional[date] = None
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
                "is_history": True
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
            User.phone == username
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
            "created_at": med.created_at.strftime("%Y-%m-%d") if med.created_at else None,
            "end_date": med.end_date,
            "last_taken_date": med.last_taken_date.isoformat() if med.last_taken_date else None
        })
    
    return resultado

@app.post("/api/cliente/{user_id}/medications", status_code=status.HTTP_201_CREATED)
async def create_medication(user_id: str, med: MedicationCreate, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    end_date = None
    if hasattr(med, 'is_continuous') and med.is_continuous:
        end_date = None  # Contínuo não tem data de fim, ou você pode colocar (date.today() + timedelta(days=3650)).strftime("%Y-%m-%d")
    elif hasattr(med, 'duration_days') and med.duration_days is not None and med.duration_days > 0:
        end_date = (date.today() + timedelta(days=med.duration_days - 1)).strftime("%Y-%m-%d")
    
    nova_med = Medication(
        user_id=user_uuid,
        name=med.name,
        dosage=med.dosage,
        time=med.time,
        days_of_week=med.days_of_week,
        is_continuous=getattr(med, 'is_continuous', False),
        end_date=end_date  # ← Apenas o VALOR da variável
    )
    
    db.add(nova_med)
    db.commit()
    db.refresh(nova_med)
    
    return {"status": "sucesso", "id": str(nova_med.id)}


# =========================================================
#  ROTAS DE ESTADO DO MEDICAMENTO (FLUXO DE 7 ESTADOS)
# =========================================================

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
    
    if hasattr(med, 'is_continuous') and med.is_continuous:
        medication.end_date = None
        medication.is_continuous = True
    elif hasattr(med, 'duration_days') and med.duration_days is not None and med.duration_days > 0:
        medication.end_date = (date.today() + timedelta(days=med.duration_days - 1)).strftime("%Y-%m-%d")
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


@app.delete("/api/medications/{med_id}")
async def delete_medication(med_id: str, db: Session = Depends(get_db)):
    """Excluir um medicamento (soft delete)"""
    try:
        med_uuid = uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    medication = db.query(Medication).filter(Medication.id == med_uuid).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medicação não encontrada")
    
    # Soft delete: apenas marca como inativo
    medication.is_active = False
    db.commit()
    
    return {"status": "sucesso", "mensagem": "Medicação excluída"}


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

# Rota fictícia para o Frontend não quebrar caso ainda tente enviar Web Push
@app.post("/api/push/subscribe")
async def dummy_subscribe():
    return {"status": "ok", "msg": "Web Push desativado. Usando WhatsApp."}

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
            
        sent_count = 0
        failed_count = 0
        
        # Para cada medicamento, busca o usuário dono dele e manda WhatsApp
        for med in meds_due:
            user = db.query(User).filter(User.id == med.user_id).first()
            if user and user.phone:
                print(f"📤 Enviando WhatsApp para {user.full_name} ({user.phone}) - Remédio: {med.name}")
                sucesso = enviar_whatsapp(user.phone, med.name, med.dosage)
                if sucesso:
                    sent_count += 1
                else:
                    failed_count += 1
            else:
                print(f"⚠️ Usuário não encontrado ou sem telefone para o medicamento {med.name}")
                failed_count += 1
                
        resultado = {
            "status": "ok",
            "hora_brasilia": current_time,
            "medicamentos_encontrados": len(meds_due),
            "whatsapp_enviados": sent_count,
            "whatsapp_falhados": failed_count
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
import pytesseract
from PIL import Image
import io
import re

@app.post("/api/prescriptions/upload")
async def upload_prescription(file: UploadFile = File(...)):
    try:
        # 1. Ler o arquivo enviado
        contents = await file.read()
        filename = file.filename.lower()
        
        raw_text = ""
        
        # Se for PDF
        if filename.endswith('.pdf') or file.content_type == 'application/pdf':
            print("📄 Arquivo recebido é um PDF. Tentando extração direta de texto...")
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(contents)) as pdf:
                    raw_text = "".join(page.extract_text() or "" for page in pdf.pages).strip()
            except Exception as e:
                print(f"⚠️ Erro ao extrair texto direto do PDF: {e}")
            
            # Se for um PDF escaneado (sem texto digital), renderizar em imagens e rodar OCR
            if not raw_text:
                print("📷 PDF escaneado (sem texto digital). Renderizando páginas em imagens para rodar OCR...")
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(io.BytesIO(contents))
                text_list = []
                for page in pdf:
                    bitmap = page.render(scale=2)  # Renderizar em boa resolução (144 DPI)
                    pil_img = bitmap.to_pil()
                    page_text = pytesseract.image_to_string(pil_img, lang='por')
                    if page_text.strip():
                        text_list.append(page_text)
                raw_text = "\n".join(text_list)
        else:
            # Se for imagem
            image = Image.open(io.BytesIO(contents))
            # 2. Extrair texto com OCR (Tesseract)
            raw_text = pytesseract.image_to_string(image, lang='por')
        
        print(f"📝 Texto extraído da receita:\n{raw_text}")
        
        # 3. Parser inteligente para extrair medicamentos
        medications = parse_medications_from_text(raw_text)
        
        if not medications:
            # Fallback se OCR não identificar padrões
            medications = [
                {"name": "Leitura parcial", "dosage": "Verifique a imagem", "frequency": "Conforme receita", "times": ["08:00"], "duration_days": 7}
            ]
        
        # 4. Retornar dados extraídos
        return JSONResponse(content={
            "success": True,
            "medications": medications,
            "raw_text_preview": raw_text[:200] + "..." if len(raw_text) > 200 else raw_text,
            "message": f"✅ {len(medications)} medicamentos identificados!"
        })
        
    except Exception as e:
        print(f"❌ Erro no OCR/Processamento: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={
            "success": True,
            "medications": [{"name": "Erro na leitura", "dosage": "Tente enviar outra imagem", "frequency": "-", "times": ["08:00"], "duration_days": 7}],
            "message": f"⚠️ Falha no OCR. Erro: {str(e)}"
        })

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

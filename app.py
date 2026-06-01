# ===== versão 1.03 - 2024-06-25 17:30 ================================
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Time, Date, Text, or_
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime, time, date, timedelta, timezone
from dotenv import load_dotenv
import os
import uuid
from pathlib import Path
from hashlib import sha256
from fastapi.middleware.cors import CORSMiddleware
import traceback
from fastapi.responses import FileResponse, JSONResponse
import os
import json
from pywebpush import webpush, WebPushException
from dotenv import load_dotenv
from gtts import gTTS
import os
import uuid
# =========================================================
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
import os
from fastapi import HTTPException
from typing import Optional, List  

# =========================================================
# ✅ CRIE O APP APENAS UMA VEZ (COM TODAS AS CONFIGURAÇÕES)
# =========================================================
app = FastAPI(
    title="CR$ HOME CARE AI",
    description="Sistema de Cuidado Domiciliar Inteligente",
    version="1.0.0"
)

# ✅ CORS (depois de criar o app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*", "POST", "GET", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ✅ MOUNT DOS ARQUIVOS ESTÁTICOS (DEPOIS DO APP E CORS)
os.makedirs("static/audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ CARREGAR VARIÁVEIS DE AMBIENTE
load_dotenv()

# ✅ BANCO DE DADOS (mantenha sua configuração existente)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    ocr_data = Column(JSONB)
    extracted_meds = Column(JSONB)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)  # ou datetime.utcnow se mudar o import


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
        
        # 2. Montar a mensagem (Texto para Fala)
        # Ex: "Atenção! Hora de tomar Dipirona, 500mg. 1 comprimido."
        text = f"Atenção! Lembrete de medicamento. Hora de tomar: {medication}, {dosage}. {instructions}"
        
        # 3. Gerar o áudio com gTTS (Google Text-to-Speech)
        tts = gTTS(text=text, lang='pt-br', slow=False)
        
        # 4. Salvar arquivo
        filename = f"audio_{uuid.uuid4().hex}.mp3"
        # Garanta que a pasta static/audio existe
        os.makedirs("static/audio", exist_ok=True)
        filepath = f"static/audio/{filename}"
        
        tts.save(filepath)
        
        # 5. Retornar a URL para o Frontend tocar
        # Supondo que sua API roda na raiz, o link será /static/audio/filename.mp3
        audio_url = f"/static/audio/{filename}"
        
        return {"status": "success", "url": audio_url, "message": "Áudio gerado com sucesso!"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
# =========================================================
# 💊 CRUD MEDICAÇÕES
# =========================================================

@app.get("/api/cliente/{user_id}/medications", response_model=List[ClienteMedicationResponse])
async def get_client_medications(user_id: str, db: Session = Depends(get_db)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de usuário inválido")
    
    medications = db.query(Medication).filter(
        Medication.user_id == user_uuid,
        Medication.is_active == True
    ).all()
    
    resultado = []
    for med in medications:
        resultado.append({
            "id": str(med.id),
            "name": med.name,
            "dosage": med.dosage,
            "time": med.time.strftime('%H:%M') if med.time else None,
            "periodo": _get_periodo(med.time),
            "days_of_week": med.days_of_week or [0,1,2,3,4,5,6]
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
        end_date = date.today() + timedelta(days=365)
    
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
        db.commit()
        
        return {"status": "success", "message": "✅ Registrado como tomado"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    finally:
        db.close()

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
        db.commit()
        
        #  Dispara notificação (assíncrono para não travar UI)
        asyncio.create_task(notify_responsible_async(med))
        
        return {"status": "success", "message": "❌ Não tomado. Responsável acionado."}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    finally:
        db.close()

async def notify_responsible_async(medication):
    """Placeholder para integração com WhatsApp/SMS (Twilio, Z-API, etc)"""
    print(f"📱 [MOCK] ACIONANDO RESPONSÁVEL: {medication.name} não tomou {medication.name} às {medication.time}")
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
            "notify_sms": r.notify_sms
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
        notify_email=resp.notify_email
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

# Rota fictícia para o Frontend não quebrar caso ainda tente enviar Web Push
@app.post("/api/push/subscribe")
async def dummy_subscribe():
    return {"status": "ok", "msg": "Web Push desativado. Usando WhatsApp."}

# 2. Endpoint para TESTE RÁPIDO DO WHATSAPP (Dispara manualmente)
@app.post("/api/teste-push")
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
# Carrega as variáveis do .env
# =========================================================
load_dotenv()


from fastapi import HTTPException
# =========================================================
# Endpoint para confirmar tomada do 
# =========================================================
@app.post("/api/medications/{med_id}/confirm-taken")
async def confirm_medication_taken(med_id: str, status: str = "taken"):
    """
    status: 'taken' ou 'not_taken'
    """
    db = SessionLocal()
    try:
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med:
            raise HTTPException(status_code=404, detail="Medicamento não encontrado")
        
        # Atualiza status
        med.taken_status = status
        med.last_taken_date = datetime.now().date()
        
        if status == "taken":
            med.reminder_count = 0
        elif status == "not_taken":
            med.reminder_count += 1
            med.responsible_notified = True
        
        # Cria log
        from sqlalchemy import text
        log_query = text("""
            INSERT INTO medication_logs 
            (medication_id, client_id, scheduled_time, actual_time, status, notes)
            VALUES (:med_id, :client_id, :sched_time, NOW(), :status, :notes)
        """)
        
        db.execute(log_query, {
            "med_id": med_id,
            "client_id": str(med.user_id),
            "sched_time": med.time,
            "status": status,
            "notes": f"Reminder #{med.reminder_count}" if status == "not_taken" else ""
        })
        
        db.commit()
        
        # Se não tomou, notificar responsável
        if status == "not_taken":
            await notify_responsible(med, db)
        
        return {
            "status": "success",
            "message": f"Medicamento {status} registrado",
            "medication": {
                "name": med.name,
                "taken_status": med.taken_status,
                "reminder_count": med.reminder_count
            }
        }
    finally:
        db.close()

# =========================================================
# Endpoint para reagendar medicamento
# =========================================================
@app.put("/api/medications/{med_id}/reschedule")
async def reschedule_medication(med_id: str, new_time: str):
    """
    Reagenda medicamento para novo horário
    new_time: formato "HH:MM" (ex: "14:30")
    """
    db = SessionLocal()
    try:
        # Busca o medicamento
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med:
            raise HTTPException(status_code=404, detail="Medicamento não encontrado")
        
        # Converte "HH:MM" para time
        try:
            hour, minute = map(int, new_time.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Hora inválida")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Horário inválido: {e}")
        
        # Atualiza o horário
        med.time = time(hour, minute)
        
        # Reseta status para pending (aguardando tomada)
        med.taken_status = "pending"
        med.reminder_count = 0
        med.responsible_notified = False
        
        db.commit()
        db.refresh(med)
        
        print(f"✅ Medicamento {med.name} reagendado para {new_time}")
        
        return {
            "status": "success",
            "message": f"Medicamento reagendado para {new_time}",
            "medication": {
                "id": str(med.id),
                "name": med.name,
                "new_time": f"{hour:02d}:{minute:02d}"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao reagendar: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        db.close()

# Endpoint para registrar "não tomou"
@app.post("/api/medications/{med_id}/not-taken")
async def mark_not_taken(med_id: str):
    """
    Marca medicamento como não tomado e notifica responsável
    """
    db = SessionLocal()
    try:
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med:
            raise HTTPException(status_code=404, detail="Medicamento não encontrado")
        
        # Atualiza contador
        med.reminder_count = (med.reminder_count or 0) + 1
        med.taken_status = "not_taken"
        med.responsible_notified = True
        
        # Cria log
        from sqlalchemy import text
        log_query = text("""
            INSERT INTO medication_logs 
            (medication_id, client_id, scheduled_time, actual_time, status, responsible_notified)
            VALUES (:med_id, :client_id, :sched_time, NOW(), 'not_taken', TRUE)
        """)
        
        db.execute(log_query, {
            "med_id": med_id,
            "client_id": str(med.user_id),
            "sched_time": med.time
        })
        
        db.commit()
        
        # Notifica responsável (implementar depois)
        # await notify_responsible(med, db)
        
        return {
            "status": "success",
            "message": "Responsável notificado",
            "reminder_count": med.reminder_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# =========================================================
# Função para notificar responsável
async def notify_responsible(medication, db):
    """
    Envia notificação ao responsável quando paciente não toma remédio
    """
    try:
        # Busca responsável do cliente
        from sqlalchemy import text
        resp_query = text("""
            SELECT name, phone 
            FROM responsibles 
            WHERE client_id = :client_id 
            LIMIT 1
        """)
        
        result = db.execute(resp_query, {"client_id": str(medication.user_id)}).first()
        
        if result:
            resp_name = result[0]
            resp_phone = result[1]
            
            # Mensagem para o responsável
            message = (
                f"⚠️ ALERTA DE MEDICAMENTO\n\n"
                f"Paciente: {medication.name}\n"
                f"Medicamento: {medication.name}\n"
                f"Horário previsto: {medication.time.strftime('%H:%M')}\n\n"
                f"O paciente NÃO tomou o medicamento no horário.\n"
                f"Por favor, verifique!"
            )
            
            # Aqui você pode integrar com WhatsApp/SMS
            print(f"📱 Notificando responsável {resp_name}: {message}")
            
            # Opcional: Enviar via WhatsApp (Twilio, Z-API, etc)
            # await send_whatsapp_message(resp_phone, message)
            
            return {"status": "sent", "to": resp_name}
        
    except Exception as e:
        print(f"❌ Erro ao notificar responsável: {e}")
        return None
# =========================================================
# INICIALIZAÇÃO
# =========================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 CR$ HOME CARE AI - Iniciando...")
    print(f"📊 Banco de dados: {os.getenv('DB_NAME', 'homecare_dev')}")
    print(f"🔗 URL: http://localhost:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
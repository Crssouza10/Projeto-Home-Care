# ===== versão 1.00
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

# Carregar variáveis de ambiente ********

load_dotenv()

app = FastAPI(
    title="CR$ HOME CARE AI",
    description="Sistema de Cuidado Domiciliar Inteligente",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Permite QUALQUER origem (desenvolvimento)
    allow_credentials=True,
    allow_methods=["*", "POST", "GET", "PUT", "DELETE"],  # ✅ Todos os métodos
    allow_headers=["*"],
)

# Configuração do Banco de Dados
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

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint = Column(Text, nullable=False, unique=True)
    subscription_info = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Criar tabelas
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Erro ao criar tabelas na inicialização (Vercel): {e}")

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
    time: time
    days_of_week: List[int] = [0,1,2,3,4,5,6]
    is_continuous: bool = False  

class MedicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    dosage: str
    time: time
    days_of_week: list
    is_active: bool
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
        end_date=end_date
    )
    
    db.add(nova_med)
    db.commit()
    db.refresh(nova_med)
    
    return {"status": "sucesso", "id": str(nova_med.id)}

@app.post("/api/medications/{med_id}/take")
async def mark_medication_taken(med_id: str, db: Session = Depends(get_db)):
    try:
        med_uuid = uuid.UUID(med_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    med = db.query(Medication).get(med_uuid)
    if not med:
        raise HTTPException(status_code=404, detail="Medicação não encontrada")
    
    return {"status": "sucesso", "mensagem": "Medicação registrada como tomada"}

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

@app.get("/sw.js")
async def get_service_worker():
    return FileResponse("sw.js", media_type="application/javascript")

# 
# ==========================================================
#  ROTAS DE NOTIFICAÇÃO PUSH (NOVO CÓDIGO)
# ==========================================================
import os
import json
from pywebpush import webpush, WebPushException

# Lista temporária para armazenar assinaturas (para teste rápido)
# Em produção, salvaríamos isso no Banco de Dados
subscriptions = [] 

# Carrega as chaves VAPID das variáveis de ambiente do Vercel
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS = {"sub": "mailto:secretary.crs.virtual@gmail.com"}

# 1. O Navegador envia sua assinatura para nós
@app.post("/api/push/subscribe")
async def subscribe(subscription: dict, db: Session = Depends(get_db)):
    try:
        endpoint = subscription.get('endpoint', '')
        if not endpoint:
            return {"status": "erro", "msg": "Endpoint ausente"}, 400
            
        # Verifica se já existe para não duplicar
        existing = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
        if not existing:
            new_sub = PushSubscription(
                endpoint=endpoint,
                subscription_info=subscription
            )
            db.add(new_sub)
            db.commit()
            print(f"✅ Nova assinatura salva no Banco: {endpoint[:30]}...")
        return {"status": "sucesso"}
    except Exception as e:
        db.rollback()
        print(f"Erro ao assinar no banco: {e}")
        return {"status": "erro"}, 500

# 2. Endpoint para TESTE RÁPIDO (Dispara manualmente)
@app.post("/api/teste-push")
async def test_push(db: Session = Depends(get_db)):
    subs_db = db.query(PushSubscription).all()
    if not subs_db:
        return {"msg": "Nenhum dispositivo inscrito no banco de dados ainda. Acesse o site no celular primeiro."}
    
    count = 0
    for sub in subs_db:
        try:
            # Envia a notificação
            webpush(
                subscription_info=sub.subscription_info,
                data=json.dumps({
                    "title": "🔔 Teste do Sistema!",
                    "body": "As notificações push estão funcionando perfeitamente (Via Banco de Dados).",
                    "icon": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
            count += 1
        except WebPushException as ex:
            print(f"Erro ao enviar push: {ex}")
            # Se der erro 410 (Gone), removemos a assinatura inválida do Banco
            if "410" in str(ex):
                db.delete(sub)
                db.commit()
            
    return {"msg": f"Tentativa de envio para {count} dispositivos."}

# 3. AGENDADOR AUTOMÁTICO (O "Cérebro" que roda a cada minuto)
@app.get("/api/check-reminders")  # ou /api/verificar-lembretes
async def check_reminders(db: Session = Depends(get_db)):
    print("🔔 [CRON] INICIANDO VERIFICAÇÃO...")
    
    try:
        # Ajuste de Fuso Horário para Brasília (UTC-3), já que o Vercel roda em UTC
        from datetime import timezone, timedelta
        now_br = datetime.now(timezone(timedelta(hours=-3)))
        current_time_str = now_br.strftime("%H:%M")
        print(f"⏰ Hora atual (Brasília): {current_time_str}")
        print(f"📋 Total de subscriptions em memória: {len(subscriptions)}")
        
        # Busca medicamentos (Usando extract para ignorar segundos e comparar só HH:MM)
        from sqlalchemy import extract
        meds_due = db.query(Medication).filter(
            extract('hour', Medication.time) == now_br.hour,
            extract('minute', Medication.time) == now_br.minute,
            Medication.is_active == True
        ).all()
        
        print(f"💊 Medicamentos encontrados: {len(meds_due)}")
        for med in meds_due:
            print(f"   - {med.name} ({med.dosage})")
        
        if not meds_due:
            return {"status": "ok", "msg": "Nenhum remédio neste horário", "hora": current_time_str}
        
        # Envia notificações
        sent = 0
        
        subs_db = db.query(PushSubscription).all()
        
        # Alerta sobre ambiente
        if not subs_db:
            print("⚠️ AVISO: Nenhuma subscription encontrada no Banco de Dados!")
            return {"status": "ok", "msg": "Remédios encontrados, mas não há dispositivos inscritos.", "hora": current_time_str, "meds": len(meds_due)}
            
        for med in meds_due:
            for sub in subs_db:
                try:
                    print(f"📤 Enviando push para {med.name}...")
                    webpush(
                        subscription_info=sub.subscription_info,
                        data=json.dumps({
                            "title": f"💊 {med.name}",
                            "body": f"Dosagem: {med.dosage}",
                            "icon": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
                        }),
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims=VAPID_CLAIMS
                    )
                    sent += 1
                except Exception as e:
                    print(f"❌ Erro ao enviar push para o endpoint: {e}")
                    if "410" in str(e):
                        db.delete(sub)
                        db.commit()
        
        return {"status": "ok", "enviados": sent, "hora": current_time_str}
        
    except Exception as e:
        print(f"💥 ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "msg": str(e)}

# =========================================================
# Carrega as variáveis do .env
# =========================================================
load_dotenv()

# Carrega as chaves VAPID
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_CLAIMS = {"sub": "mailto:secretary.crs.virtual@gmail.com"}

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
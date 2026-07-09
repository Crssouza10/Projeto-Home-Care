"""
CR$ HOME CARE AI - Motor de Agendamento de Medicamentos
========================================================
Implementa as regras de recorrência 5a, 5b, 5c, 5d.

Regra 5a: Curta duração (ex: 2 dias)
  - Marca APENAS nos dias específicos dentro do período.
  - Ex: segunda 07/07 e terça 08/07 → só esses 2 dias.

Regra 5b: Dia específico por X semanas
  - Ex: toda quarta-feira por 7 semanas →
    09/07, 16/07, 23/07, 30/07, 06/08, 13/08, 20/08

Regra 5c: Contínuo diário por 6 meses
  - Gera doses diárias + flag review_needed_at = start + 180 dias
  - Após 6 meses, sistema alerta "consulte seu médico para revisar"

Regra 5d: Extensível para novos padrões (ex: dias alternados, etc.)
"""

from datetime import date, time, datetime, timedelta
from typing import List, Dict, Optional
import uuid


def generate_medication_schedules(
    user_id: uuid.UUID,
    medication_id: uuid.UUID,
    med_time: time,
    days_of_week: List[int],
    start_date: date,
    duration_days: Optional[int] = None,
    end_date: Optional[date] = None,
    is_continuous: bool = False,
    continuous_months: int = 6,
) -> List[Dict]:
    """
    Gera a lista de schedules para um medicamento.

    Parâmetros:
        user_id: UUID do usuário
        medication_id: UUID do medicamento
        med_time: horário de administração (time)
        days_of_week: lista de dias da semana (0=Dom, 1=Seg, ..., 6=Sáb)
        start_date: data de início do tratamento
        duration_days: duração em dias (para regras 5a, 5b)
        end_date: data final explícita (alternativa a duration_days)
        is_continuous: True = regra 5c (contínuo diário)
        continuous_months: meses para medicação contínua (default 6)

    Retorna:
        Lista de dicts: {scheduled_date, scheduled_time, status}
    """
    schedules = []

    # Converter days_of_week: se veio vazio, tratar como todos os dias [0..6]
    if not days_of_week:
        days_of_week = [0, 1, 2, 3, 4, 5, 6]

    # Determinar data final
    if end_date is None and duration_days is not None and duration_days > 0:
        end_date = start_date + timedelta(days=duration_days - 1)
    elif end_date is None and is_continuous:
        end_date = start_date + timedelta(days=continuous_months * 30)  # ~180 dias
    elif end_date is None:
        # Se não tem duração nem é contínuo, assume 30 dias padrão
        end_date = start_date + timedelta(days=29)

    # Se days_of_week tem dias específicos (não é todos os dias)
    # REGRA 5a e 5b: só gera schedules nos dias da semana configurados
    current = start_date
    while current <= end_date:
        py_weekday = current.weekday()  # 0=Seg, 6=Dom (Python)
        # Converter para nosso formato: 0=Dom, 1=Seg, ..., 6=Sáb
        custom_day = 0 if py_weekday == 6 else py_weekday + 1

        if custom_day in days_of_week:
            schedules.append({
                "scheduled_date": current,
                "scheduled_time": med_time,
                "status": "pending",
            })

        current += timedelta(days=1)

    return schedules


def get_schedule_summary(
    schedules: List[Dict],
    days_of_week: List[int],
    start_date: date,
    end_date: Optional[date],
) -> Dict:
    """
    Retorna um resumo legível do agendamento para exibição.
    """
    dias_nomes = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

    if not schedules:
        return {
            "total_dias": 0,
            "texto": "Nenhum dia de administração",
            "periodo": "",
        }

    dias_semana_str = ", ".join(dias_nomes[d] for d in days_of_week) if days_of_week else "Todos os dias"

    primeiro = schedules[0]["scheduled_date"]
    ultimo = schedules[-1]["scheduled_date"]

    return {
        "total_dias": len(schedules),
        "texto": f"{len(schedules)} dias de administração",
        "dias_semana": dias_semana_str,
        "periodo": f"{primeiro.strftime('%d/%m/%Y')} até {ultimo.strftime('%d/%m/%Y')}",
        "primeiro_dia": primeiro.isoformat(),
        "ultimo_dia": ultimo.isoformat(),
    }


# ============================================================
# Função auxiliar: converter dia da semana Python → nosso formato
# ============================================================
def python_weekday_to_custom(py_day: int) -> int:
    """Converte 0=Seg (Python) → 0=Dom, 1=Seg, ..., 6=Sáb"""
    if py_day == 6:  # Domingo em Python
        return 0
    return py_day + 1


def custom_weekday_to_python(custom_day: int) -> int:
    """Converte 0=Dom, ..., 6=Sáb → 0=Seg (Python)"""
    if custom_day == 0:
        return 6
    return custom_day - 1


# ============================================================
# Cálculo de data de revisão (Regra 5c)
# ============================================================
def get_review_date(start_date: date, continuous_months: int = 6) -> date:
    """Retorna a data em que o paciente deve revisar a medicação contínua."""
    return start_date + timedelta(days=continuous_months * 30)


def is_review_needed(start_date: date, continuous_months: int = 6) -> bool:
    """Verifica se a medicação contínua já passou do prazo de revisão."""
    return date.today() >= get_review_date(start_date, continuous_months)

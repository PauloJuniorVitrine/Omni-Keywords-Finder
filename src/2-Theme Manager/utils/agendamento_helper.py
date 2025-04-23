# theme_manager/utils/agendamento_helper.py

from datetime import datetime, time, date
from enum import Enum
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dias_semana = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6
}

class StatusCategoria(Enum):
    EXECUTAR = "executar"
    FORA_DO_DIA = "fora_do_dia"
    FORA_DO_HORARIO = "fora_do_horario"
    FORA_DA_JANELA = "fora_da_janela"

def dia_semana_em_int(dia_nome: str) -> int:
    """
    Converte o nome do dia da semana (ex: 'segunda') para inteiro (0 a 6).
    """
    dia_normalizado = dia_nome.strip().lower()
    if dia_normalizado not in dias_semana:
        raise ValueError(f"Dia da semana inválido: '{dia_nome}'")
    return dias_semana[dia_normalizado]

def hora_atual_igual_ou_maior(hora_execucao: time, agora: time = None) -> bool:
    """
    Verifica se o horário atual é igual ou posterior ao horário agendado.
    """
    agora = agora or datetime.now().time()
    return agora >= hora_execucao

def data_entre_intervalo(data_inicio: date, data_fim: date, hoje: date = None) -> bool:
    """
    Verifica se a data atual está entre as datas de início e fim, inclusive.
    """
    hoje = hoje or date.today()
    return data_inicio <= hoje <= data_fim

def validar_parametros_agendamento(hora_execucao, data_inicio, data_fim):
    """
    Garante que os parâmetros possuem tipos corretos.
    """
    if not isinstance(hora_execucao, time):
        raise ValueError("Hora de execução deve ser do tipo datetime.time")
    if not isinstance(data_inicio, date) or not isinstance(data_fim, date):
        raise ValueError("Datas de coleta devem ser do tipo datetime.date")

def status_categoria(
    dia_semana: str,
    hora_execucao: time,
    data_inicio: date,
    data_fim: date,
    agora: datetime = None,
    debug: bool = False
) -> StatusCategoria:
    """
    Determina o status da categoria com base na data, hora e dia da semana.

    Retornos possíveis (Enum):
    - StatusCategoria.EXECUTAR
    - StatusCategoria.FORA_DO_DIA
    - StatusCategoria.FORA_DO_HORARIO
    - StatusCategoria.FORA_DA_JANELA
    """
    validar_parametros_agendamento(hora_execucao, data_inicio, data_fim)

    agora = agora or datetime.now()
    hoje = agora.date()
    hora_atual = agora.time()
    dia_atual = agora.weekday()

    if not data_entre_intervalo(data_inicio, data_fim, hoje):
        status = StatusCategoria.FORA_DA_JANELA
    elif dia_semana_em_int(dia_semana) != dia_atual:
        status = StatusCategoria.FORA_DO_DIA
    elif not hora_atual_igual_ou_maior(hora_execucao, hora_atual):
        status = StatusCategoria.FORA_DO_HORARIO
    else:
        status = StatusCategoria.EXECUTAR

    if debug:
        logger.info(
            f"[Agendamento] STATUS: {status.value} | "
            f"Dia: {dia_semana} | Hora: {hora_execucao} | "
            f"Hoje: {hoje} ({dia_atual}) | Hora atual: {hora_atual} | "
            f"Intervalo: {data_inicio} → {data_fim}"
        )

    return status

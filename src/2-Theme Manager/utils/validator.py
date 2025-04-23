# theme_manager/utils/validator.py

from datetime import date, time

def validar_data(data):
    """Valida se a data fornecida é uma instância válida de 'date'."""
    if not isinstance(data, date):
        raise ValueError("Data inválida. O valor deve ser do tipo 'date'.")
    return True

def validar_intervalo_datas(data_inicio, data_fim):
    """Valida se a data de início não é posterior à data de término."""
    if data_inicio > data_fim:
        raise ValueError("A data de início não pode ser posterior à data de término.")
    return True

def validar_hora(hora):
    """Valida se a hora fornecida é uma instância válida de 'time' e se está no intervalo correto."""
    if not isinstance(hora, time):
        raise ValueError("Hora inválida. O valor deve ser do tipo 'time'.")
    if hora < time(0, 0) or hora > time(23, 59):
        raise ValueError("A hora fornecida está fora do intervalo válido.")
    return True

def validar_dia_semana(dia):
    """Valida se o dia da semana fornecido é válido."""
    dias_validos = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    if dia.lower() not in dias_validos:
        raise ValueError(f"Dia da semana inválido: {dia}")
    return True

def validar_tamanho_campo(campo, min_len=3, max_len=100):
    """Valida se o campo está dentro do intervalo de tamanho permitido."""
    if len(campo) < min_len or len(campo) > max_len:
        raise ValueError(f"O campo deve ter entre {min_len} e {max_len} caracteres.")
    return True

def validar_campos_obrigatorios(campos):
    """Valida se os campos obrigatórios estão preenchidos."""
    obrigatorios = ["nicho", "tema", "descricao"]
    for campo in obrigatorios:
        if not campos.get(campo):
            raise ValueError(f"Campo obrigatório {campo} não preenchido.")
    return True

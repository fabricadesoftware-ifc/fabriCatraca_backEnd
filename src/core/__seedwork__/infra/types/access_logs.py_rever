from typing import TypedDict, Optional
from enum import IntEnum


class AccessRuleEvent(IntEnum):
    EQUIPAMENTO_INVALIDO                  = 1
    PARÂMETROS_DE_IDENTIFICAÇÃO_INVALIDOS = 2
    NÃO_IDENTIFICADO                      = 3
    IDENTIFICAÇÃO_PENDENTE                = 4
    TEMPO_DE_IDENTIFICAÇÃO_ESGOTADO       = 5
    ACESSO_NEGADO                         = 6
    ACESSO_CONCEDIDO                      = 7
    ACESSO_PENDENTE                       = 8 # (usado quando o acesso depende de mais de uma pessoa)
    USUÁRIO_NÃO_É_ADMINISTRADOR           = 9 # (usado quando um usuário tenta acessar o menu mas não é administrador)
    ACESSO_NÃO_IDENTIFICADO               = 10 # (quando o portal é aberto através da API e o motivo não é informado)
    ACESSO_POR_BOTOEIRA                   = 11
    ACESSO_PELA_INTERFACE_WEB             = 12
    DESISTÊNCIA_DE_ENTRADA                = 13
    SEM_RESPOSTA                          = 14 # (nenhuma ação é tomada)
    ACESSO_PELA_INTERFONIA                = 15


class AccessLogData(TypedDict):
    id: int
    time: int
    event: AccessRuleEvent
    device_id: int
    identifier_id: int
    user_id: int
    portal_id: int
    identification_rule_id: int
    qrcode_value: str
    uhf_tag: str
    pin_value: str 
    card_value: int
    confidence: int
    mask: int
    log_type_id: int
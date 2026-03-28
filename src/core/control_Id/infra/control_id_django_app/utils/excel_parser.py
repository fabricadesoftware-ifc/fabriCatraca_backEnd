import logging
import re
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

SHEET_NAME_PATTERN = re.compile(r"(\d+)([A-Za-z]+)(\d+)\s*\((\d+)\)")
REQUIRED_COLUMNS = ["ORDEM", "Matrícula", "Nome"]
EXCEL_EXTENSION_PATTERN = re.compile(r".*\.xlsx$")


@dataclass
class ParsedRow:
    name: str
    registration: str


@dataclass
class ParsedSheet:
    sheet_name: str
    group_name: str
    rows: list[ParsedRow]


def is_valid_excel(filename: str) -> bool:
    return bool(EXCEL_EXTENSION_PATTERN.match(filename))


def parse_sheet_name(sheet_name: str) -> str | None:
    """
    Extrai o nome do grupo a partir do nome da aba.
    Ex: '1INFO1(2025)' → '1INFO1', '3quimi2(2025)' → '3QUIMI2'
    """
    match = SHEET_NAME_PATTERN.match(sheet_name)
    if not match:
        return None
    nivel = match.group(1)
    curso = match.group(2).upper()
    secao = match.group(3)
    return f"{nivel}{curso}{secao}"


def parse_sheet(
    tmp_path: str, sheet_name: str
) -> tuple[ParsedSheet | None, str | None]:
    """
    Lê uma aba do Excel e retorna os dados parseados.
    Retorna (ParsedSheet, None) em sucesso ou (None, mensagem_de_erro) em falha.
    """
    df = pd.read_excel(tmp_path, sheet_name=sheet_name)

    if len(df.columns) != 3:
        return None, f"Sheet '{sheet_name}': esperado 3 colunas (ORDEM, Matrícula, Nome)"

    df.columns = REQUIRED_COLUMNS

    if df.empty:
        return None, f"Sheet '{sheet_name}': sem dados"

    group_name = parse_sheet_name(sheet_name)
    if not group_name:
        return None, f"Sheet '{sheet_name}': formato inválido. Esperado: '1INFO1(2025)'"

    rows = []
    row_errors = []

    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        if pd.isna(row["Matrícula"]) or pd.isna(row["Nome"]):
            row_errors.append(
                f"Sheet '{sheet_name}', linha {row_number}: Matrícula ou Nome vazio"
            )
            continue
        rows.append(ParsedRow(
            name=str(row["Nome"]).strip(),
            registration=str(row["Matrícula"]).strip(),
        ))

    if row_errors:
        for err in row_errors:
            logger.warning(f"[IMPORT] {err}")

    if not rows:
        logger.warning(f"[IMPORT] Aba '{sheet_name}' sem linhas válidas — pulando")
        return None, None

    logger.info(f"[IMPORT] Aba '{sheet_name}': {len(rows)} aluno(s) válido(s)")

    parsed = ParsedSheet(
        sheet_name=sheet_name,
        group_name=group_name,
        rows=rows,
    )
    return parsed, None

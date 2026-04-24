import logging
import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

SHEET_NAME_PATTERN = re.compile(r"(\d+)([A-Za-z]+)(\d+)\s*\((\d+)\)")
REQUIRED_COLUMNS = ["ORDEM", "Matrícula", "Nome"]
EXCEL_EXTENSION_PATTERN = re.compile(r".*\.xlsx$")
CSV_EXTENSION_PATTERN = re.compile(r".*\.csv$")
CSV_REQUIRED_COLUMNS = ["matricula", "discente ou nome"]


@dataclass
class ParsedRow:
    name: str
    registration: str
    birth_date: date | None = None
    phone: str | None = None
    phone_landline: str | None = None
    email: str | None = None


@dataclass
class ParsedSheet:
    sheet_name: str
    group_name: str
    rows: list[ParsedRow]


def is_valid_excel(filename: str) -> bool:
    return bool(EXCEL_EXTENSION_PATTERN.match(filename.lower()))


def is_valid_csv(filename: str) -> bool:
    return bool(CSV_EXTENSION_PATTERN.match(filename.lower()))


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


def _blank_to_none(value) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def _parse_birth_date(value) -> date | None:
    if pd.isna(value) or value in ("", None):
        return None
    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _find_column(columns: list[str], aliases: list[str]) -> str | None:
    for alias in aliases:
        if alias in columns:
            return alias
    return None


def parse_discente_csv(tmp_path: str) -> tuple[ParsedSheet | None, str | None]:
    """
    Le CSV/TSV exportado com campos de discentes.
    O arquivo de exemplo vem separado por tabulacao, mas sep=None tambem aceita CSV comum.
    """
    try:
        df = pd.read_csv(
            tmp_path,
            sep=None,
            engine="python",
            dtype=str,
            encoding="utf-8-sig",
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            tmp_path,
            sep=None,
            engine="python",
            dtype=str,
            encoding="latin1",
        )

    df.columns = [str(column).strip().lower() for column in df.columns]

    columns = list(df.columns)
    registration_column = _find_column(columns, ["matricula", "matrícula"])
    name_column = _find_column(columns, ["discente", "nome", "nome_completo"])
    birth_date_column = _find_column(columns, ["data_nascimento", "nascimento"])
    mobile_phone_column = _find_column(columns, ["telefone_celular", "celular"])
    landline_phone_column = _find_column(columns, ["telefone_fixo", "telefone"])
    email_column = _find_column(columns, ["email", "e-mail"])

    missing_columns = []
    if not registration_column:
        missing_columns.append("matricula")
    if not name_column:
        missing_columns.append("discente ou nome")
    if missing_columns:
        return None, (
            "CSV: colunas obrigatorias ausentes: "
            f"{', '.join(missing_columns)}"
        )

    rows = []
    row_errors = []

    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        registration = _blank_to_none(row.get(registration_column))
        name = _blank_to_none(row.get(name_column))

        if not registration or not name:
            row_errors.append(
                f"CSV, linha {row_number}: matricula ou discente vazio"
            )
            continue

        phone = _blank_to_none(row.get(mobile_phone_column)) or _blank_to_none(
            row.get(landline_phone_column)
        )

        rows.append(
            ParsedRow(
                name=name,
                registration=registration,
                birth_date=_parse_birth_date(row.get(birth_date_column)),
                phone=phone,
                phone_landline=_blank_to_none(row.get(landline_phone_column)),
                email=_blank_to_none(row.get(email_column)),
            )
        )

    if row_errors:
        for err in row_errors:
            logger.warning(f"[IMPORT] {err}")

    if not rows:
        return None, "CSV: nenhuma linha valida encontrada"

    return ParsedSheet(
        sheet_name="CSV",
        group_name="",
        rows=rows,
    ), None

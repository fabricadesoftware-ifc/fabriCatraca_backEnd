import re


def normalize_cpf(value):
    if value in ("", None):
        return None

    digits = re.sub(r"\D", "", value)
    if len(digits) != 11:
        raise ValueError("CPF deve estar no formato 000.000.000-00.")

    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def normalize_phone(value):
    if value in ("", None):
        return None

    digits = re.sub(r"\D", "", value)
    if len(digits) not in (10, 11):
        raise ValueError(
            "Telefone deve estar no formato (00) 0000-0000 ou (00) 00000-0000."
        )

    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"

    return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"


def validate_user_dates(attrs):
    start_date = attrs.get("start_date")
    end_date = attrs.get("end_date")

    if start_date and end_date and start_date > end_date:
        raise ValueError(
            "A data de início de vigência não pode ser maior que a data final de vigência."
        )

    return False

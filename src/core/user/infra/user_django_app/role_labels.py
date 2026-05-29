from django.conf import settings


DEFAULT_APP_ROLE_LABELS = {
    "": "Sem perfil",
    "admin": "Administrador",
    "guarita": "Guarita",
    "sisae": "SISAE",
    "aluno": "Aluno",
    "servidor": "Servidor",
}


def get_app_role_labels() -> dict[str, str]:
    configured_labels = getattr(settings, "APP_ROLE_LABELS", {})
    labels = DEFAULT_APP_ROLE_LABELS.copy()
    if isinstance(configured_labels, dict):
        labels.update(configured_labels)

    return {
        role: str(labels.get(role, fallback)).strip() or fallback
        for role, fallback in DEFAULT_APP_ROLE_LABELS.items()
    }


def get_app_role_label(role: str | None) -> str:
    labels = get_app_role_labels()
    normalized_role = role or ""
    return labels.get(normalized_role, normalized_role or labels[""])

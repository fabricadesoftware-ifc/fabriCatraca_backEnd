from __future__ import annotations

from typing import Any

from rest_framework.response import Response


def api_error_response(
    error: str,
    *,
    code: str,
    details: Any = None,
    status_code: int = 400,
) -> Response:
    payload = {
        "error": error,
        "code": code,
    }
    if details is not None:
        payload["details"] = details

    return Response(payload, status=status_code)

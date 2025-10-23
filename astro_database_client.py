"""Lightweight client for the external astrological database service.

This module centralises the logic for calling the online endpoints used by the
pipeline so that each script no longer depends on local CSV snapshots.  The
client expects the following environment variables:

``ASTRO_DB_BASE_URL``
    Base URL for the API (e.g. ``https://api.example.com``).
``ASTRO_DB_API_KEY`` (optional)
    Token that will be sent as a ``Bearer`` header when provided.
``ASTRO_DB_TIMEOUT`` (optional)
    Request timeout (in seconds). Defaults to 30 seconds.

Specific endpoints can also be overridden with the variables below when the API
structure diverges from the defaults used in this project:

- ``ASTRO_DB_PEOPLE_ENDPOINT`` (default: ``/people``)
- ``ASTRO_DB_CLEANED_ENDPOINT`` (default: ``/people/cleaned``)
- ``ASTRO_DB_REDUCED_ENDPOINT`` (default: ``/people/reduced``)
- ``ASTRO_DB_FEATURES_ENDPOINT`` (default: ``/astro-features``)
- ``ASTRO_DB_PREPARED_ENDPOINT`` (default: ``/ml/prepared``)

Each ``fetch_*`` helper returns a list of dictionaries ready to be converted
into a ``pandas.DataFrame`` by the caller.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger(__name__)


class AstroDatabaseError(RuntimeError):
    """Raised when the astrological database cannot be reached or returns bad data."""


@dataclass
class _EndpointConfig:
    base_url: str
    path: str

    def build_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.path.lstrip('/')}"


class AstroDatabaseClient:
    """HTTP client that knows how to talk to the remote astrological database."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        base_url = base_url or os.getenv("ASTRO_DB_BASE_URL")
        if not base_url:
            raise AstroDatabaseError(
                "ASTRO_DB_BASE_URL não está configurada. Defina a URL do banco astrológico "
                "com a variável de ambiente ASTRO_DB_BASE_URL."
            )

        self._base_url = base_url
        self._api_key = api_key or os.getenv("ASTRO_DB_API_KEY")
        timeout_val = timeout if timeout is not None else os.getenv("ASTRO_DB_TIMEOUT", "30")
        try:
            self._timeout = float(timeout_val)
        except ValueError as exc:  # pragma: no cover - configuração incorreta pouco comum
            raise AstroDatabaseError(
                f"Valor inválido para ASTRO_DB_TIMEOUT: {timeout_val!r}. Informe número em segundos."
            ) from exc

        self._session = session or requests.Session()

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------
    def fetch_people(self, limit: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        return self._request(
            os.getenv("ASTRO_DB_PEOPLE_ENDPOINT", "/people"),
            limit=limit,
            filters=filters,
        )

    def fetch_cleaned_people(self, limit: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        return self._request(
            os.getenv("ASTRO_DB_CLEANED_ENDPOINT", "/people/cleaned"),
            limit=limit,
            filters=filters,
        )

    def fetch_reduced_people(self, limit: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        return self._request(
            os.getenv("ASTRO_DB_REDUCED_ENDPOINT", "/people/reduced"),
            limit=limit,
            filters=filters,
        )

    def fetch_astrological_features(self, limit: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        return self._request(
            os.getenv("ASTRO_DB_FEATURES_ENDPOINT", "/astro-features"),
            limit=limit,
            filters=filters,
        )

    def fetch_prepared_ml_dataset(self, limit: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        return self._request(
            os.getenv("ASTRO_DB_PREPARED_ENDPOINT", "/ml/prepared"),
            limit=limit,
            filters=filters,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _request(
        self,
        path: str,
        *,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        config = _EndpointConfig(base_url=self._base_url, path=path)
        params = self._build_params(limit=limit, filters=filters)
        headers = self._build_headers()
        url = config.build_url()

        logger.debug("Consultando banco astrológico: %s", url)

        try:
            response = self._session.get(url, headers=headers, params=params, timeout=self._timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AstroDatabaseError(f"Falha ao consultar {url}: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AstroDatabaseError(f"Resposta inválida recebida de {url}: {exc}") from exc

        data = self._extract_list(payload)
        if not isinstance(data, list):
            raise AstroDatabaseError(
                "Resposta inesperada do banco astrológico. Esperado lista de registros, "
                f"mas foi recebido: {payload!r}"
            )

        logger.info("Banco astrológico retornou %s registros de %s", len(data), url)
        return data

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    @staticmethod
    def _build_params(
        *, limit: Optional[int] = None, filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if filters:
            params.update({k: v for k, v in filters.items() if v is not None})
        return params or None

    @staticmethod
    def _extract_list(payload: Any) -> Any:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("results", "data", "items", "records"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return payload


__all__ = ["AstroDatabaseClient", "AstroDatabaseError"]

"""
astrum_geocode.py
Geocodificacao de cidade -> lat/lon + fuso horario.
Usa Nominatim (OpenStreetMap) -- gratuito, sem chave de API.
"""

from __future__ import annotations

import asyncio
import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Fusos brasileiros (horas em relacao ao UTC, sem DST)
BR_TIMEZONES: dict[str, float] = {
    "acre":                    -5.0,
    "amazonas":                -4.0,
    "rondonia":                -4.0,
    "roraima":                 -4.0,
    "para":                    -3.0,
    "amapa":                   -3.0,
    "tocantins":               -3.0,
    "maranhao":                -3.0,
    "piaui":                   -3.0,
    "ceara":                   -3.0,
    "rio grande do norte":     -3.0,
    "paraiba":                 -3.0,
    "pernambuco":              -3.0,
    "alagoas":                 -3.0,
    "sergipe":                 -3.0,
    "bahia":                   -3.0,
    "minas gerais":            -3.0,
    "espirito santo":          -3.0,
    "rio de janeiro":          -3.0,
    "sao paulo":               -3.0,
    "parana":                  -3.0,
    "santa catarina":          -3.0,
    "rio grande do sul":       -3.0,
    "mato grosso":             -4.0,
    "mato grosso do sul":      -4.0,
    "goias":                   -3.0,
    "distrito federal":        -3.0,
}

# Cache em memoria (evita chamadas repetidas)
_geo_cache: dict[str, tuple[float, float, float]] = {}


async def geocode(city: str, country: str = "Brazil") -> tuple[float, float, float]:
    """
    Retorna (lat, lon, tz_offset) para uma cidade.
    tz_offset: horas de UTC (ex: -3.0 para Brasilia)
    """
    cache_key = f"{city.lower()}|{country.lower()}"
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": f"{city}, {country}",
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers={"User-Agent": "ASTRUM-Portal/1.0 (astrum@astrum.app)"},
            )
            data = resp.json()

        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            tz  = _estimate_timezone(city, country, lon)
            result: tuple[float, float, float] = (lat, lon, tz)
            _geo_cache[cache_key] = result
            return result

    except Exception as e:
        print(f"[geocode] Erro para '{city}, {country}': {e}")

    # Fallback: Sao Paulo
    return (-23.5505, -46.6333, -3.0)


def _estimate_timezone(city: str, country: str, lon: float) -> float:
    """
    Estima o fuso horario.
    Para Brasil: usa tabela por estado.
    Para outros paises: estimativa pela longitude.
    """
    country_lower = country.lower()

    if "brazil" in country_lower or "brasil" in country_lower:
        # Normalizar: remover acentos ASCII-safe para lookup
        city_norm = _normalize(city.lower())
        for keyword, tz in BR_TIMEZONES.items():
            if keyword in city_norm:
                return tz
        return -3.0  # padrao Brasil

    # Estimativa generica por longitude
    tz = round(lon / 15.0)
    return max(-12.0, min(14.0, float(tz)))


def _normalize(text: str) -> str:
    """Remove acentos simples para comparacao com chaves da tabela."""
    replacements = {
        "a": ["a", "a", "a", "a"],
        "e": ["e", "e"],
        "i": ["i", "i"],
        "o": ["o", "o", "o"],
        "u": ["u", "u"],
        "c": ["c"],
        "n": ["n"],
    }
    result = text
    for base, variants in replacements.items():
        for v in variants:
            try:
                result = result.replace(v, base)
            except Exception:
                pass
    return result


def geocode_sync(city: str, country: str = "Brazil") -> tuple[float, float, float]:
    """Versao sincrona para uso fora de contexto async."""
    return asyncio.run(geocode(city, country))

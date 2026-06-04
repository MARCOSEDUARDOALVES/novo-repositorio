"""
astrum_transits.py — Trânsitos e Revolução Solar ASTRUM
========================================================
Trânsitos:       comparação dos planetas atuais com o mapa natal.
Revolução Solar: momento exato em que o Sol retorna à longitude natal.

A Revolução Solar usa busca iterativa em 3 fases (1h → 1min → 10s).
Funciona com pyswisseph (prod) ou com ephem (dev) via calculate_chart.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from astrum_chart import (
    _USE_SWE, calculate_chart, degree_to_sign, find_house,
    ASPECT_DEFS, ASPECT_PLANETS,
)

# pyswisseph só disponível em prod; usado apenas para SR de alta precisão
if _USE_SWE:
    import swisseph as swe

# ── Constantes ────────────────────────────────────────────────────────────────

TRANSIT_PLANETS = {
    "Sol", "Mercurio", "Venus", "Marte",
    "Jupiter", "Saturno", "Urano", "Netuno", "Plutao",
}

TRANSIT_ORBS: dict[str, float] = {
    "Sol": 3.0, "Mercurio": 2.0, "Venus": 2.0, "Marte": 3.0,
    "Jupiter": 4.0, "Saturno": 4.0, "Urano": 3.0,
    "Netuno": 3.0, "Plutao": 3.0,
}

TRANSIT_WEIGHT: dict[str, int] = {
    "Plutao": 10, "Netuno": 9, "Urano": 8, "Saturno": 7,
    "Jupiter": 6, "Marte": 5, "Sol": 4, "Venus": 3, "Mercurio": 2,
}


# ── Trânsitos ─────────────────────────────────────────────────────────────────

def calculate_transits(
    natal_chart: dict,
    current_date: Optional[str] = None,
    current_time: str = "12:00",
) -> dict:
    """
    Compara posições planetárias atuais com o mapa natal.
    Retorna lista de aspectos em trânsito, ordenada por importância.
    """
    if not current_date:
        current_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Posições atuais — via calculate_chart (funciona nos dois engines)
    # lat/lon não afeta posições planetárias (só o Asc/casas)
    current_chart = calculate_chart(
        current_date, current_time, lat=-23.55, lon=-46.63, tz_offset=0.0
    )
    current_planets = [
        p for p in current_chart.get("planets", [])
        if p["name"] in TRANSIT_PLANETS
    ]

    natal_planets = [
        p for p in natal_chart.get("planets", [])
        if p["name"] in ASPECT_PLANETS
    ]
    natal_cusps = [h["cusp"] for h in natal_chart.get("houses", [])]

    transits: list[dict] = []
    for tp in current_planets:
        orb_limit = TRANSIT_ORBS.get(tp["name"], 3.0)
        for np_ in natal_planets:
            diff = abs(tp["longitude"] - np_["longitude"])
            if diff > 180:
                diff = 360.0 - diff
            for asp_name, asp in ASPECT_DEFS.items():
                orb = abs(diff - asp["angle"])
                if orb <= orb_limit:
                    transits.append({
                        "transitPlanet":     tp["name"],
                        "transitSign":       tp["sign"],
                        "transitDegree":     tp["degree"],
                        "transitRetrograde": tp["isRetrograde"],
                        "natalPlanet":       np_["name"],
                        "natalSign":         np_["sign"],
                        "natalHouse":        np_.get("house", 0),
                        "aspect":            asp_name,
                        "symbol":            asp["symbol"],
                        "orb":               round(orb, 3),
                        "exact":             orb < 0.5,
                        "nature":            asp["nature"],
                        "weight":            TRANSIT_WEIGHT.get(tp["name"], 1),
                    })
                    break  # um aspecto por par

    transits.sort(key=lambda x: (-x["weight"], x["orb"]))

    # Planetas em trânsito pelas casas natais
    in_houses: list[dict] = []
    if natal_cusps:
        for tp in current_planets:
            in_houses.append({
                "planet":    tp["name"],
                "sign":      tp["sign"],
                "house":     find_house(tp["longitude"], natal_cusps),
                "retrograde": tp["isRetrograde"],
            })

    return {
        "transits":         transits,
        "transitsInHouses": in_houses,
        "currentPositions": current_planets,
        "period":           current_date,
        "totalAspects":     len(transits),
    }


# ── Revolução Solar ───────────────────────────────────────────────────────────

def calculate_solar_return(
    natal_chart: dict,
    birth_date: str,
    birth_time: str,
    lat: float,
    lon: float,
    year: Optional[int] = None,
) -> dict:
    """
    Encontra o momento exato em que o Sol retorna à longitude natal.

    Com pyswisseph: precisão de ~segundos via busca iterativa 1h→1min→10s.
    Com ephem (dev): busca horária simples (precisão ~30 min — suficiente para dev).
    """
    if not year:
        year = datetime.utcnow().year

    natal_sun = next(
        (p for p in natal_chart.get("planets", []) if p["name"] == "Sol"), None
    )
    if not natal_sun:
        raise ValueError("Mapa natal nao contem o Sol")

    natal_sun_lon = natal_sun["longitude"]

    # Data de partida da busca: 5 dias antes do aniversário no ano alvo
    birth_md = birth_date[5:]  # MM-DD
    try:
        anniversary = datetime.strptime(f"{year}-{birth_md}", "%Y-%m-%d")
    except ValueError:
        anniversary = datetime.strptime(f"{year}-03-01", "%Y-%m-%d")  # 29-fev em ano comum

    search_start = anniversary - timedelta(days=5)

    if _USE_SWE:
        # Alta precisão: 3 fases iterativas
        best_jd = _find_sun_return_swe(natal_sun_lon, search_start, steps=240, delta=timedelta(hours=1))
        if best_jd:
            refined_start = _jd_to_datetime(best_jd) - timedelta(hours=12)
            best_jd = _find_sun_return_swe(natal_sun_lon, refined_start, steps=1440, delta=timedelta(minutes=1))
        if best_jd:
            exact_start = _jd_to_datetime(best_jd) - timedelta(minutes=30)
            best_jd = _find_sun_return_swe(natal_sun_lon, exact_start, steps=360, delta=timedelta(seconds=10))
        sr_dt = _jd_to_datetime(best_jd) if best_jd else anniversary
    else:
        # Dev: busca horária via ephem
        sr_dt = _find_sun_return_ephem(natal_sun_lon, search_start, steps=240)

    sr_chart = calculate_chart(
        sr_dt.strftime("%Y-%m-%d"),
        sr_dt.strftime("%H:%M"),
        lat, lon, tz_offset=0.0,
    )
    sr_chart["solarReturnYear"]    = year
    sr_chart["exactDatetimeUTC"]   = sr_dt.isoformat() + "Z"
    sr_chart["natalSunLongitude"]  = natal_sun_lon

    return sr_chart


# ── Helpers internos ──────────────────────────────────────────────────────────

def _find_sun_return_swe(
    target_lon: float,
    start: datetime,
    steps: int,
    delta: timedelta,
) -> Optional[float]:
    """Busca iterativa com pyswisseph. Retorna JD do Sol mais próximo a target_lon."""
    best_jd: Optional[float] = None
    best_diff = 360.0
    current = start
    for _ in range(steps):
        jd = swe.julday(
            current.year, current.month, current.day,
            current.hour + current.minute / 60.0 + current.second / 3600.0,
        )
        sun_pos, _ = swe.calc_ut(jd, swe.SUN)
        diff = abs(sun_pos[0] - target_lon)
        if diff > 180:
            diff = 360.0 - diff
        if diff < best_diff:
            best_diff = diff
            best_jd = jd
        current += delta
    return best_jd


def _find_sun_return_ephem(
    target_lon: float,
    start: datetime,
    steps: int,
) -> datetime:
    """Busca horária simples com ephem. Para uso em dev."""
    import ephem as ephem_lib
    import math

    best_dt = start
    best_diff = 360.0
    current = start
    for _ in range(steps):
        d_str = f"{current.year}/{current.month}/{current.day} {current.hour:02d}:{current.minute:02d}:00"
        d = ephem_lib.Date(d_str)
        sun = ephem_lib.Sun()
        sun.compute(d, epoch=ephem_lib.J2000)
        ecl = ephem_lib.Ecliptic(sun, epoch=ephem_lib.J2000)
        lon_deg = math.degrees(float(ecl.lon)) % 360.0
        diff = abs(lon_deg - target_lon)
        if diff > 180:
            diff = 360.0 - diff
        if diff < best_diff:
            best_diff = diff
            best_dt = current
        current += timedelta(hours=1)
    return best_dt


def _jd_to_datetime(jd: float) -> datetime:
    """Converte Dia Juliano (UT) para datetime UTC. Requer pyswisseph."""
    result = swe.jdut1_to_utc(jd, 1)  # gregório
    year, month, day = int(result[0]), int(result[1]), int(result[2])
    hour_frac = result[3]
    hour   = int(hour_frac)
    minute = int((hour_frac - hour) * 60)
    second = int(((hour_frac - hour) * 60 - minute) * 60)
    return datetime(year, month, day, hour, minute, max(0, second))

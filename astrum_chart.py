"""
astrum_chart.py — Motor de cálculo astronômico ASTRUM
======================================================
Estratégia dual de backend:
  - pyswisseph  → produção (Railway/Linux) — Swiss Ephemeris, precisão profissional
  - ephem       → desenvolvimento (Windows sem compilador C) — PyEphem, sem build

A saída é idêntica nos dois casos. O frontend nunca sabe qual engine está ativo.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

# ── Selecionar engine automaticamente ────────────────────────────────────────
try:
    import swisseph as swe
    from pathlib import Path
    swe.set_ephe_path(str(Path(__file__).parent / "ephe"))
    _USE_SWE = True
    print("[chart] engine: pyswisseph (producao)")
except ImportError:
    import ephem as ephem_lib          # nome explícito — sem conflito
    _USE_SWE = False
    print("[chart] engine: ephem (modo dev)")

# ── Constantes ────────────────────────────────────────────────────────────────
SIGNS_PT = [
    "Aries", "Touro", "Gemeos", "Cancer", "Leao", "Virgem",
    "Libra", "Escorpiao", "Sagitario", "Capricornio", "Aquario", "Peixes",
]

# IDs pyswisseph para cada planeta (usados apenas quando _USE_SWE=True)
_SWE_IDS: dict[str, int] = {}
if _USE_SWE:
    _SWE_IDS = {
        "Sol": swe.SUN, "Lua": swe.MOON, "Mercurio": swe.MERCURY,
        "Venus": swe.VENUS, "Marte": swe.MARS, "Jupiter": swe.JUPITER,
        "Saturno": swe.SATURN, "Urano": swe.URANUS, "Netuno": swe.NEPTUNE,
        "Plutao": swe.PLUTO, "Nodo Norte": swe.MEAN_NODE, "Quiron": swe.CHIRON,
    }

ASPECT_DEFS: dict[str, dict] = {
    "conjuncao":      {"angle": 0,   "orb": 8.0, "nature": "fusion",      "symbol": "c"},
    "oposicao":       {"angle": 180, "orb": 8.0, "nature": "tension",     "symbol": "o"},
    "trigono":        {"angle": 120, "orb": 7.0, "nature": "flow",        "symbol": "t"},
    "quadratura":     {"angle": 90,  "orb": 7.0, "nature": "challenge",   "symbol": "q"},
    "sextil":         {"angle": 60,  "orb": 5.0, "nature": "opportunity", "symbol": "s"},
    "quincuncio":     {"angle": 150, "orb": 3.0, "nature": "adjustment",  "symbol": "Q"},
    "semissextil":    {"angle": 30,  "orb": 2.0, "nature": "mild",        "symbol": "S"},
    "semiquadrado":   {"angle": 45,  "orb": 2.0, "nature": "friction",    "symbol": "Z"},
    "sesquiquadrado": {"angle": 135, "orb": 2.0, "nature": "friction",    "symbol": "R"},
}

ASPECT_PLANETS = {
    "Sol", "Lua", "Mercurio", "Venus", "Marte",
    "Jupiter", "Saturno", "Urano", "Netuno", "Plutao", "Quiron",
}

DIGNITY_TABLE: dict[str, dict[str, list[str]]] = {
    "Sol":     {"domicilio": ["Leao"],              "exaltacao": ["Aries"],
                "exilio":    ["Aquario"],            "queda":     ["Libra"]},
    "Lua":     {"domicilio": ["Cancer"],             "exaltacao": ["Touro"],
                "exilio":    ["Capricornio"],         "queda":     ["Escorpiao"]},
    "Mercurio":{"domicilio": ["Gemeos","Virgem"],    "exaltacao": ["Virgem"],
                "exilio":    ["Sagitario","Peixes"],  "queda":     ["Peixes"]},
    "Venus":   {"domicilio": ["Touro","Libra"],      "exaltacao": ["Peixes"],
                "exilio":    ["Escorpiao","Aries"],   "queda":     ["Virgem"]},
    "Marte":   {"domicilio": ["Aries","Escorpiao"],  "exaltacao": ["Capricornio"],
                "exilio":    ["Libra","Touro"],       "queda":     ["Cancer"]},
    "Jupiter": {"domicilio": ["Sagitario","Peixes"], "exaltacao": ["Cancer"],
                "exilio":    ["Gemeos","Virgem"],     "queda":     ["Capricornio"]},
    "Saturno": {"domicilio": ["Capricornio","Aquario"],"exaltacao":["Libra"],
                "exilio":    ["Cancer","Leao"],       "queda":     ["Aries"]},
    "Urano":   {"domicilio": ["Aquario"],            "exaltacao": ["Escorpiao"],
                "exilio":    ["Leao"],                "queda":     ["Touro"]},
    "Netuno":  {"domicilio": ["Peixes"],             "exaltacao": ["Leao"],
                "exilio":    ["Virgem"],              "queda":     ["Capricornio"]},
    "Plutao":  {"domicilio": ["Escorpiao"],          "exaltacao": ["Aries"],
                "exilio":    ["Touro"],               "queda":     ["Libra"]},
}
DIGNITY_POWER = {"domicilio": 5, "exaltacao": 4, "neutro": 3, "exilio": 2, "queda": 1}


# ── Helpers comuns ────────────────────────────────────────────────────────────

def degree_to_sign(longitude: float) -> tuple[str, float]:
    longitude = longitude % 360.0
    idx = int(longitude // 30)
    deg = longitude % 30.0
    return SIGNS_PT[idx], round(deg, 4)


def degree_to_dms(degree: float) -> str:
    """Formata grau como '28°47' para exibição no frontend."""
    d = int(degree)
    m = int((degree - d) * 60)
    return f"{d}°{m:02d}'"


def find_house(planet_lon: float, cusps: list[float]) -> int:
    """Determina a casa (1-12) de uma longitude eclíptica."""
    lon = planet_lon % 360.0
    for i in range(12):
        c1 = cusps[i] % 360.0
        c2 = cusps[(i + 1) % 12] % 360.0
        if c2 < c1:
            if lon >= c1 or lon < c2:
                return i + 1
        else:
            if c1 <= lon < c2:
                return i + 1
    return 1


def _planet_entry(name: str, lon: float, lat: float, speed: float, cusps: list[float]) -> dict:
    sign, deg = degree_to_sign(lon)
    return {
        "name":           name,
        "longitude":      round(lon, 4),
        "latitude":       round(lat, 4),
        "sign":           sign,
        "degree":         round(deg, 4),
        "degreeFormatted": degree_to_dms(deg),
        "speed":          round(speed, 4),
        "isRetrograde":   speed < 0,
        "house":          find_house(lon, cusps) if cusps else 0,
    }


def calculate_aspects(planets: list[dict]) -> list[dict]:
    main = [p for p in planets if p["name"] in ASPECT_PLANETS]
    aspects: list[dict] = []
    for i in range(len(main)):
        for j in range(i + 1, len(main)):
            p1, p2 = main[i], main[j]
            diff = abs(p1["longitude"] - p2["longitude"])
            if diff > 180:
                diff = 360.0 - diff
            for asp_name, asp in ASPECT_DEFS.items():
                orb = abs(diff - asp["angle"])
                if orb <= asp["orb"]:
                    aspects.append({
                        "planet_a": p1["name"],  "planet_b": p2["name"],
                        "aspect":   asp_name,    "symbol":   asp["symbol"],
                        "orb":      round(orb, 3), "exact":  orb < 1.0,
                        "nature":   asp["nature"],
                        "sign_a":   p1["sign"],  "sign_b":   p2["sign"],
                        "house_a":  p1.get("house", 0),
                        "house_b":  p2.get("house", 0),
                    })
                    break  # um aspecto por par
    return sorted(aspects, key=lambda x: x["orb"])


def calculate_dignities(planets: list[dict]) -> list[dict]:
    result: list[dict] = []
    for planet in planets:
        name = planet["name"]
        sign = planet["sign"]
        if name not in DIGNITY_TABLE:
            continue
        dignity = "neutro"
        for dtype, signs in DIGNITY_TABLE[name].items():
            if sign in signs:
                dignity = dtype
                break
        result.append({
            "planet":     name,
            "sign":       sign,
            "dignity":    dignity,
            "powerLevel": DIGNITY_POWER.get(dignity, 3),
            "isStrong":   dignity in ("domicilio", "exaltacao"),
            "isWeak":     dignity in ("exilio", "queda"),
        })
    return result


# ── Backend pyswisseph ────────────────────────────────────────────────────────

def _swe_calc(date: str, time: str, lat: float, lon: float,
              tz_offset: float, house_system: bytes) -> tuple:
    dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    hour_ut = dt.hour + dt.minute / 60.0 - tz_offset
    jd = swe.julday(dt.year, dt.month, dt.day, hour_ut)

    planets: list[dict] = []
    for name, pid in _SWE_IDS.items():
        try:
            res, _ = swe.calc_ut(jd, pid)
            planets.append(_planet_entry(name, res[0], res[1], res[3], []))
        except Exception as e:
            print(f"[chart/swe] {name}: {e}")

    cusps_raw, ascmc = swe.houses(jd, lat, lon, house_system)
    cusps = list(cusps_raw)
    for p in planets:
        p["house"] = find_house(p["longitude"], cusps)

    asc_lon, mc_lon = ascmc[0], ascmc[1]
    return planets, cusps, asc_lon, mc_lon, jd


# ── Backend ephem (dev) ───────────────────────────────────────────────────────

def _ephem_calc(date: str, time: str, lat: float, lon: float,
                tz_offset: float) -> tuple:
    dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    hour_ut = dt.hour + dt.minute / 60.0 - tz_offset
    d_str = f"{dt.year}/{dt.month}/{dt.day} {int(hour_ut):02d}:{int((hour_ut % 1) * 60):02d}:00"
    d = ephem_lib.Date(d_str)

    obs = ephem_lib.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.date = d
    obs.pressure = 0
    obs.epoch = ephem_lib.J2000

    BODIES: dict[str, object] = {
        "Sol":     ephem_lib.Sun(),
        "Lua":     ephem_lib.Moon(),
        "Mercurio":ephem_lib.Mercury(),
        "Venus":   ephem_lib.Venus(),
        "Marte":   ephem_lib.Mars(),
        "Jupiter": ephem_lib.Jupiter(),
        "Saturno": ephem_lib.Saturn(),
        "Urano":   ephem_lib.Uranus(),
        "Netuno":  ephem_lib.Neptune(),
        "Plutao":  ephem_lib.Pluto(),
    }

    planets: list[dict] = []
    for name, body in BODIES.items():
        body.compute(d, epoch=ephem_lib.J2000)
        ecl = ephem_lib.Ecliptic(body, epoch=ephem_lib.J2000)
        lon_deg = math.degrees(float(ecl.lon)) % 360.0
        lat_deg = math.degrees(float(ecl.lat))
        planets.append(_planet_entry(name, lon_deg, lat_deg, 1.0, []))

    # Sidereal time → Ascendente
    # ephem.sidereal_time() retorna LMST em radianos onde 2π = 24h (= 360° de AR)
    lst_rad = float(obs.sidereal_time())          # 0 … 2π
    ramc_deg = math.degrees(lst_rad) % 360.0      # RAMC em graus (0-360)
    ramc_r   = math.radians(ramc_deg)

    # Obliquidade atual (aproximação linear; suficiente para ±1°)
    jd_approx = ephem_lib.julian_date(d)
    T = (jd_approx - 2451545.0) / 36525.0
    obliquity = 23.439291111 - 0.013004167 * T    # graus
    obl_r = math.radians(obliquity)
    lat_r = math.radians(lat)

    # MC: atan2(sin(RAMC), cos(RAMC)×cos(ε))  → quadrante correto
    mc_lon = math.degrees(math.atan2(math.sin(ramc_r),
                                     math.cos(ramc_r) * math.cos(obl_r))) % 360.0

    # Ascendente (fórmula de Chauvenet / Braha):
    #   tan(ASC) = -cos(RAMC) / (sin(RAMC)×cos(ε) + tan(φ)×sin(ε))
    asc_y = -math.cos(ramc_r)
    asc_x = math.sin(ramc_r) * math.cos(obl_r) + math.tan(lat_r) * math.sin(obl_r)
    asc_lon = math.degrees(math.atan2(asc_y, asc_x)) % 360.0

    # Correção de quadrante: quando asc_x > 0 (horizonte no semiespaço leste),
    # o atan2 retorna Q1/Q4 mas o Ascendente real está 180° à frente.
    if asc_x > 0:
        asc_lon = (asc_lon + 180.0) % 360.0

    # Whole Sign cusps
    asc_idx = int(asc_lon // 30)
    cusps = [(asc_idx * 30 + i * 30) % 360.0 for i in range(12)]

    for p in planets:
        p["house"] = find_house(p["longitude"], cusps)

    return planets, cusps, asc_lon, mc_lon, 0.0  # jd=0 no modo dev


# ── API pública ───────────────────────────────────────────────────────────────

def calculate_chart(
    date: str,
    time: str,
    lat: float,
    lon: float,
    tz_offset: float = -3.0,
    house_system: bytes = b"P",
) -> dict:
    """
    Calcula o mapa natal completo.
    Retorna estrutura padronizada independente do engine.
    """
    if _USE_SWE:
        planets, cusps, asc_lon, mc_lon, jd = _swe_calc(
            date, time, lat, lon, tz_offset, house_system
        )
    else:
        planets, cusps, asc_lon, mc_lon, jd = _ephem_calc(
            date, time, lat, lon, tz_offset
        )

    # ── Nodo Sul (oposto ao Norte) ────────────────────────────────────────────
    nn = next((p for p in planets if p["name"] == "Nodo Norte"), None)
    if nn:
        south_lon = (nn["longitude"] + 180.0) % 360.0
        s_sign, s_deg = degree_to_sign(south_lon)
        planets.append({
            "name": "Nodo Sul", "longitude": round(south_lon, 4),
            "latitude": 0.0, "sign": s_sign, "degree": round(s_deg, 4),
            "degreeFormatted": degree_to_dms(s_deg),
            "speed": nn["speed"], "isRetrograde": True,
            "house": find_house(south_lon, cusps),
        })

    # ── Parte da Fortuna (Asc + Lua − Sol) ───────────────────────────────────
    sol = next((p for p in planets if p["name"] == "Sol"), None)
    lua = next((p for p in planets if p["name"] == "Lua"), None)
    if sol and lua:
        fort_lon = (asc_lon + lua["longitude"] - sol["longitude"]) % 360.0
        f_sign, f_deg = degree_to_sign(fort_lon)
        planets.append({
            "name": "Fortuna", "longitude": round(fort_lon, 4),
            "latitude": 0.0, "sign": f_sign, "degree": round(f_deg, 4),
            "degreeFormatted": degree_to_dms(f_deg),
            "speed": 0.0, "isRetrograde": False,
            "house": find_house(fort_lon, cusps),
        })

    # ── Casas ─────────────────────────────────────────────────────────────────
    houses = []
    for i, cusp in enumerate(cusps, 1):
        sign, deg = degree_to_sign(cusp)
        houses.append({
            "number": i, "sign": sign,
            "degree": round(deg, 4), "cusp": round(cusp, 4),
            "formatted": degree_to_dms(deg),
        })

    # ── Derivados ─────────────────────────────────────────────────────────────
    aspects   = calculate_aspects(planets)
    dignities = calculate_dignities(planets)
    asc_sign, _ = degree_to_sign(asc_lon)
    mc_sign,  _ = degree_to_sign(mc_lon)
    dsc_sign, _ = degree_to_sign((asc_lon + 180.0) % 360.0)
    ic_sign,  _ = degree_to_sign((mc_lon  + 180.0) % 360.0)
    sun_sign  = next((p["sign"] for p in planets if p["name"] == "Sol"), "")
    moon_sign = next((p["sign"] for p in planets if p["name"] == "Lua"), "")

    return {
        "planets":         planets,
        "houses":          houses,
        "aspects":         aspects,
        "dignities":       dignities,
        "ascendant":       asc_sign,
        "ascendantDegree": round(asc_lon, 4),
        "midheaven":       mc_sign,
        "midheavenDegree": round(mc_lon, 4),
        "descendant":      dsc_sign,
        "imumCoeli":       ic_sign,
        "sun":             sun_sign,
        "moon":            moon_sign,
        "engine":          "pyswisseph" if _USE_SWE else "ephem-dev",
        "calculatedAt":    datetime.utcnow().isoformat() + "Z",
    }

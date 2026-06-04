"""
astrum_interpreter.py
Monta o contexto rico (tabelas + aspectos + dignidades) para o LLM.
O LLM recebe dados estruturados precisos -- nao genericos.
"""

from __future__ import annotations

import json
from pathlib import Path

from astrum_db import get_conn


def build_chart_context(chart: dict, include_aspects: bool = True) -> str:
    """
    Constroi o contexto textual completo do mapa para o prompt LLM.
    Consulta as tabelas de keywords/arquetipos para cada posicao.
    """
    lines: list[str] = []
    conn = get_conn()
    try:
        # -- Pontos Angulares --------------------------------------------------
        lines.append("=== PONTOS ANGULARES ===")
        lines.append(
            f"Ascendente: {chart.get('ascendant', '-')} | MC: {chart.get('midheaven', '-')}"
        )
        lines.append(
            f"Descendente: {chart.get('descendant', '-')} | IC: {chart.get('imumCoeli', '-')}"
        )
        lines.append("")

        # -- Planetas com contexto das tabelas ---------------------------------
        lines.append("=== PLANETAS NO MAPA ===")
        for planet in chart.get("planets", []):
            name  = planet["name"]
            sign  = planet["sign"]
            house = planet.get("house", 0)
            retro = " [R]" if planet.get("isRetrograde") else ""
            deg   = planet.get("degreeFormatted", f"{planet.get('degree', 0):.1f}*")

            row = conn.execute(
                """SELECT keywords, shadow_keywords, jungian_archetype,
                          jungian_notes, freudian_note, element, modality
                   FROM planet_sign_keywords
                   WHERE planet=? AND sign=?""",
                (name, sign),
            ).fetchone()

            if row:
                kw       = json.loads(row["keywords"] or "[]")
                shadow   = json.loads(row["shadow_keywords"] or "[]")
                archetype = row["jungian_archetype"] or ""
                jnotes   = row["jungian_notes"] or ""
                fnotes   = row["freudian_note"] or ""
                element  = row["element"] or ""
                modality = row["modality"] or ""

                lines.append(
                    f"* {name} em {sign} ({deg}), Casa {house}{retro}"
                    f" | Elemento: {element} {modality}"
                )
                lines.append(f"  Arquetipo: {archetype}")
                lines.append(f"  Dons: {', '.join(kw[:4])}")
                lines.append(f"  Sombra: {', '.join(shadow[:3])}")
                lines.append(f"  Jung: {jnotes[:180]}...")
                lines.append(f"  Freud: {fnotes[:120]}...")
            else:
                lines.append(f"* {name} em {sign} ({deg}), Casa {house}{retro}")

            lines.append("")

        # -- Casas com contexto -----------------------------------------------
        lines.append("=== CASAS ATIVADAS ===")
        for house in chart.get("houses", []):
            num  = house["number"]
            sign = house["sign"]
            row = conn.execute(
                "SELECT name_pt, life_area, jungian_theme FROM house_meanings WHERE house=?",
                (num,),
            ).fetchone()
            if row:
                lines.append(
                    f"Casa {num} -- {row['name_pt']} ({sign}): {row['life_area']}"
                )
            else:
                lines.append(f"Casa {num} ({sign})")
        lines.append("")

        # -- Aspectos mais significativos -------------------------------------
        if include_aspects:
            aspects = chart.get("aspects", [])
            if aspects:
                lines.append("=== ASPECTOS PRINCIPAIS ===")
                weight: dict[str, int] = {
                    "Plutao": 10, "Netuno": 9, "Urano": 8, "Saturno": 7,
                    "Jupiter": 6, "Marte": 5, "Sol": 4, "Lua": 4,
                    "Venus": 3, "Mercurio": 2, "Quiron": 3,
                }
                scored = sorted(
                    aspects,
                    key=lambda a: (
                        -(weight.get(a["planet_a"], 1) + weight.get(a["planet_b"], 1)),
                        a["orb"],
                    ),
                )[:8]

                for asp in scored:
                    exact = " [EXATO]" if asp.get("exact") else ""
                    row = conn.execute(
                        """SELECT theme, psychological FROM aspect_meanings
                           WHERE ((planet_a=? AND planet_b=?) OR (planet_a=? AND planet_b=?))
                           AND aspect=? LIMIT 1""",
                        (
                            asp["planet_a"], asp["planet_b"],
                            asp["planet_b"], asp["planet_a"],
                            asp["aspect"],
                        ),
                    ).fetchone()

                    note = f" -> {row['theme']}" if row else ""
                    lines.append(
                        f"  {asp['symbol']} {asp['planet_a']} x {asp['planet_b']}"
                        f" ({asp['aspect']}, orbe {asp['orb']:.1f}*){exact}{note}"
                    )
                    if row and row["psychological"]:
                        lines.append(f"    {row['psychological'][:200]}...")
                lines.append("")

        # -- Dignidades -------------------------------------------------------
        dignities = chart.get("dignities", [])
        strong = [d for d in dignities if d.get("isStrong")]
        weak   = [d for d in dignities if d.get("isWeak")]

        if strong:
            lines.append("=== PLANETAS EM FORCA ===")
            for d in strong:
                lines.append(
                    f"  [+] {d['planet']} em {d['dignity']} em {d['sign']}"
                    f" (poder {d['powerLevel']}/5)"
                )
            lines.append("")

        if weak:
            lines.append("=== PLANETAS ENFRAQUECIDOS ===")
            for d in weak:
                lines.append(
                    f"  [-] {d['planet']} em {d['dignity']} em {d['sign']}"
                    f" (poder {d['powerLevel']}/5)"
                )
            lines.append("")

    finally:
        conn.close()

    return "\n".join(lines)


def get_house_context(house_number: int) -> dict:
    """Retorna os dados completos de uma casa do banco."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM house_meanings WHERE house=?", (house_number,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {}
    return dict(row)


def get_planet_sign_context(planet: str, sign: str) -> dict:
    """Retorna keywords e arquetipos de um planeta em um signo."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM planet_sign_keywords WHERE planet=? AND sign=?",
            (planet, sign),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {}
    d = dict(row)
    d["keywords"]        = json.loads(d.get("keywords") or "[]")
    d["shadow_keywords"] = json.loads(d.get("shadow_keywords") or "[]")
    return d


def get_aspect_context(planet_a: str, planet_b: str, aspect: str) -> dict:
    """Retorna a interpretacao de um aspecto especifico."""
    conn = get_conn()
    try:
        row = conn.execute(
            """SELECT * FROM aspect_meanings
               WHERE ((planet_a=? AND planet_b=?) OR (planet_a=? AND planet_b=?))
               AND aspect=? LIMIT 1""",
            (planet_a, planet_b, planet_b, planet_a, aspect),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {}
    d = dict(row)
    d["keywords"] = json.loads(d.get("keywords") or "[]")
    return d

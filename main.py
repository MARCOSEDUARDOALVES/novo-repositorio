"""
ASTRUM -- Backend Principal
FastAPI + Swiss Ephemeris + SQLite + LLM

Endpoints:
  GET  /health
  POST /natal-chart          -> calcula mapa natal (Swiss Ephemeris)
  POST /interpret-natal      -> interpretacao completa (LLM + tabelas)
  POST /transits             -> transitos atuais vs mapa natal
  POST /interpret-transits   -> interpretacao dos transitos (LLM)
  POST /solar-return         -> Revolucao Solar calculada
  POST /interpret-solar      -> interpretacao da RS (LLM)
  POST /astrologo/chat       -> chat com Prof. Aurelio (LLM + contexto do mapa)
  POST /astrum-interpret     -> endpoint generico de prompt (fallback do frontend)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from astrum_chart       import calculate_chart
from astrum_transits    import calculate_transits, calculate_solar_return
from astrum_interpreter import build_chart_context
from astrum_geocode     import geocode
from astrum_llm         import generate
from astrum_db          import init_db

load_dotenv()


# ── Lifespan (substitui o on_event depreciado) ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("[ASTRUM] Backend iniciado. Banco de dados pronto.")
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ASTRUM Backend",
    description="Motor astrologico com Swiss Ephemeris e interpretacao por IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class BirthRequest(BaseModel):
    date:      str
    time:      str
    city:      str
    country:   str = "Brasil"
    lat:       Optional[float] = None
    lon:       Optional[float] = None
    tz_offset: Optional[float] = None


class InterpretNatalRequest(BaseModel):
    chart:     dict
    user_name: str
    gender:    str = "neutro"


class TransitsRequest(BaseModel):
    natal_chart:  dict
    current_date: Optional[str] = None
    city:         Optional[str] = None
    country:      Optional[str] = "Brasil"


class InterpretTransitsRequest(BaseModel):
    transits_result: dict
    natal_chart:     dict
    user_name:       str
    gender:          str = "neutro"


class SolarReturnRequest(BaseModel):
    natal_chart: dict
    birth_date:  str
    birth_time:  str
    city:        str
    country:     str = "Brasil"
    lat:         Optional[float] = None
    lon:         Optional[float] = None
    year:        Optional[int] = None


class InterpretSolarRequest(BaseModel):
    solar_chart: dict
    natal_chart: dict
    user_name:   str
    gender:      str = "neutro"
    year:        Optional[int] = None


class ChatRequest(BaseModel):
    natal_chart:    dict
    user_name:      str
    gender:         str = "neutro"
    question:       str
    history:        list = []
    questions_left: int = 5


class GenericPromptRequest(BaseModel):
    prompt: str


class AskRequest(BaseModel):
    """Endpoint de Q&A focado: responde uma pergunta com base no contexto fornecido.
    Não roda pipeline de interpretação — apenas passa o prompt para o LLM."""
    context:   str            # trechos relevantes já extraídos do mapa
    question:  str            # pergunta do usuário
    user_name: str = "Consultante"
    history:   list = []      # histórico recente da conversa


# ── Helpers ───────────────────────────────────────────────────────────────────

async def resolve_location(
    city: str,
    country: str,
    lat: Optional[float],
    lon: Optional[float],
    tz_offset: Optional[float],
) -> tuple[float, float, float]:
    """Geocodifica ou usa lat/lon fornecido."""
    if lat is not None and lon is not None:
        tz = tz_offset if tz_offset is not None else -3.0
        return lat, lon, tz
    return await geocode(city, country)


def pronouns(gender: str) -> dict:
    """Retorna conjunto de pronomes para o genero."""
    if gender == "feminino":
        return {"subj": "ela", "poss": "sua", "art": "a", "obj": "ela"}
    if gender == "masculino":
        return {"subj": "ele", "poss": "seu", "art": "o", "obj": "ele"}
    return {"subj": "a pessoa", "poss": "seu/sua", "art": "o/a", "obj": "a pessoa"}


# ── Persona Prof. Aurelio ─────────────────────────────────────────────────────

AURELIO_SYSTEM = (
    "Voce e o **Prof. Aurelio**, Astrologo Freudiano -- um mestre que une a precisao "
    "matematica da astrologia tradicional com a psicologia analitica de Carl Gustav Jung "
    "e a psicanalise de Sigmund Freud.\n\n"
    "Seu metodo:\n"
    "- Usa os dados exatos do mapa natal (planetas, casas, aspectos, dignidades) para "
    "fundamentar cada afirmacao\n"
    "- Interpreta cada posicao planetaria como expressao de um arquetipo junguiano\n"
    "- Identifica complexos psicologicos freudianos nas tensoes do mapa\n"
    "- Revela padroes inconscientes com gentileza e firmeza\n"
    "- Nunca e superficial -- cada frase tem profundidade e especificidade\n"
    "- Usa portugues brasileiro elegante, nao coloquial\n"
    "- Escreve em **negrito** os conceitos-chave"
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ASTRUM Backend", "version": "1.0.0"}


@app.post("/natal-chart")
async def natal_chart_endpoint(body: BirthRequest):
    """Calcula o mapa natal completo. Retorna planetas, casas, aspectos, dignidades."""
    try:
        lat, lon, tz = await resolve_location(
            body.city, body.country, body.lat, body.lon, body.tz_offset
        )
        chart = calculate_chart(body.date, body.time, lat, lon, tz_offset=tz)
        chart["birthCity"]    = body.city
        chart["birthCountry"] = body.country
        chart["lat"]          = lat
        chart["lon"]          = lon
        chart["tz"]           = tz
        return chart
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no calculo: {str(e)}")


@app.post("/interpret-natal")
async def interpret_natal_endpoint(body: InterpretNatalRequest):
    """
    Interpreta o mapa natal completo com LLM + tabelas de conhecimento.
    Chamada custosa -- resultado deve ser cacheado permanentemente no Firestore.
    """
    try:
        chart   = body.chart
        name    = body.user_name
        pron    = pronouns(body.gender)
        context = build_chart_context(chart, include_aspects=True)

        # ── Mapa de regentes tradicionais + modernos ──────────────────────────
        REGENTES = {
            "Aries":       "Marte",
            "Touro":       "Venus",
            "Gemeos":      "Mercurio",
            "Cancer":      "Lua",
            "Leao":        "Sol",
            "Virgem":      "Mercurio",
            "Libra":       "Venus",
            "Escorpiao":   "Plutao",   # moderno; tradicional: Marte
            "Sagitario":   "Jupiter",
            "Capricornio": "Saturno",
            "Aquario":     "Urano",    # moderno; tradicional: Saturno
            "Peixes":      "Netuno",   # moderno; tradicional: Jupiter
        }

        planets_list = chart.get("planets", [])
        houses_list  = chart.get("houses",  [])

        # Índice rápido: nome do planeta → dados
        pl_idx = {pl["name"]: pl for pl in planets_list}

        def pl_str(planet_name: str) -> str:
            """Retorna 'signo, Casa N [R]' do planeta."""
            pl = pl_idx.get(planet_name)
            if not pl:
                return "nao encontrado"
            retro = " (Retr.)" if pl.get("isRetrograde") else ""
            return f"{pl['sign']}, Casa {pl['house']}{retro}"

        def dispositor_chain(sign: str, visited: set = None) -> str:
            """Monta a cadeia de dispositores de um signo até o domicílio."""
            if visited is None:
                visited = set()
            reg_name = REGENTES.get(sign)
            if not reg_name or reg_name in visited:
                return ""
            visited.add(reg_name)
            reg = pl_idx.get(reg_name)
            if not reg:
                return f"{reg_name} (nao calculado)"
            retro = " Retr." if reg.get("isRetrograde") else ""
            chain = f"{reg_name} em {reg['sign']}{retro}, Casa {reg['house']}"
            # Verifica domicilio (para encerrar a cadeia)
            dom_signs = {
                "Sol": ["Leao"], "Lua": ["Cancer"], "Mercurio": ["Gemeos","Virgem"],
                "Venus": ["Touro","Libra"], "Marte": ["Aries","Escorpiao"],
                "Jupiter": ["Sagitario","Peixes"], "Saturno": ["Capricornio","Aquario"],
                "Urano": ["Aquario"], "Netuno": ["Peixes"], "Plutao": ["Escorpiao"],
            }
            if reg["sign"] in dom_signs.get(reg_name, []):
                return chain + " [domicilio]"
            next_chain = dispositor_chain(reg["sign"], visited)
            return chain + (" → " + next_chain if next_chain else "")

        def planets_in_house(house_num: int) -> str:
            """Lista planetas que estão na casa especificada."""
            pls = [pl for pl in planets_list if pl.get("house") == house_num
                   and pl["name"] not in ("Fortuna", "Nodo Sul")]
            if not pls:
                return "vazia"
            parts = []
            for pl in pls:
                r = " (Retr.)" if pl.get("isRetrograde") else ""
                parts.append(f"{pl['name']} em {pl['sign']}{r}")
            return ", ".join(parts)

        # ── Monta bloco de casas para o prompt ────────────────────────────────
        house_blocks = []
        HOUSE_THEMES = [
            "identidade, corpo, mascara social (Persona de Jung)",
            "recursos materiais, autoestima, valores — o que eu possuo e valoro",
            "mente, comunicacao, irmaos, aprendizado — o pensamento consciente",
            "raizes, familia, lar, mae — complexo materno e base psiquica",
            "criatividade, romance, filhos, prazer — o Eros e expressao do ego",
            "trabalho, saude, servico, rotina — o Id disciplinado",
            "parceria, casamento, o Outro — projecao da Sombra (Jung)",
            "sexualidade, morte, transformacao, legados — o inconsciente profundo",
            "filosofia, viagens, crencas, visao de mundo — o Superego espiritual",
            "carreira, reputacao, autoridade, pai — complexo paterno",
            "amigos, grupos, ideais, futuro — o eu coletivo",
            "inconsciente, isolamento, karma, espiritualidade — o retorno ao todo",
        ]
        for h in houses_list:
            num  = h["number"]
            sign = h["sign"]
            reg  = REGENTES.get(sign, "?")
            reg_pos = pl_str(reg)
            chain   = dispositor_chain(sign)
            in_h    = planets_in_house(num)
            theme   = HOUSE_THEMES[num - 1] if num <= 12 else ""
            house_blocks.append(
                f"Casa {num} ({sign}) — regente: {reg} em {reg_pos}\n"
                f"  Cadeia: {chain}\n"
                f"  Planetas na casa: {in_h}\n"
                f"  Tema psicologico: {theme}"
            )

        houses_text = "\n\n".join(house_blocks)

        # ── Aspectos relevantes ────────────────────────────────────────────────
        aspects_list = chart.get("aspects", [])[:10]
        aspects_text = "\n".join([
            f"  {a['planet_a']} {a.get('symbol','x')} {a['planet_b']} "
            f"({a['aspect']}, orbe {a['orb']:.1f}{'R' if a.get('exact') else ''})"
            for a in aspects_list
        ]) or "nenhum aspecto calculado"

        asc_sign = chart.get("ascendant", "?")
        mc_sign  = chart.get("midheaven", "?")

        prompt = f"""{AURELIO_SYSTEM}

---

## MAPA NATAL COMPLETO — {name.upper()}

Ascendente: {asc_sign} | Meio do Ceu: {mc_sign}

### CASAS E DISPOSITORES:
{houses_text}

### ASPECTOS PRINCIPAIS:
{aspects_text}

---

## SUA MISSAO — INTERPRETACAO CASA A CASA

Elabore a interpretacao psicologica e astrologica profunda de {name}, **casa a casa**.
Estilo: Prof. Aurelio — psicanalize freudiana + psicologia analitica junguiana aplicadas a astrologia.
Lingua: portugues brasileiro elegante. Use a ortografia com acentos.

ESTRUTURA OBRIGATORIA — para cada casa:

**✦ Casa 1 — [signo] — [tema da casa]**
Interprete: (1) o signo na cuspide e como molda a identidade/mascara; (2) o regente e sua posicao — o que isso significa psicologicamente; (3) a cadeia de dispositores — como a energia flui e onde termina; (4) planetas presentes na casa — se houver, como intensificam a tematica; (5) complexo freudiano ou arquetipo jungiano ativado nesta casa para {name} especificamente.

Repita este padrao para todas as 12 casas.

**✦ Sintese Integrativa**
O padrao dominante do mapa: arquetipo central, complexo principal, missao de alma. A cadeia de dispositores que conecta tudo. Mensagem final do Prof. Aurelio para {name}.

---

REGRAS ABSOLUTAS:
- CITE sempre posicoes exatas: "Seu Plutao em Libra na Casa 12, regendo o Ascendente Escorpiao..."
- Mencione a CADEIA DE DISPOSITORES de cada casa com o significado psicologico
- Use **negrito** nos conceitos-chave astrologicos e psicologicos
- NUNCA frases genericas — cada frase deve ser impossivel de aplicar a outro mapa
- NUNCA se apresente — comece direto na Casa 1
- Minimo 3 paragrafos por casa"""

        interpretation = await generate(prompt, temperature=0.78, max_tokens=5000)
        return {
            "interpretation": interpretation,
            "generatedAt": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na interpretacao: {str(e)}")


@app.post("/transits")
async def transits_endpoint(body: TransitsRequest):
    """Calcula transitos atuais sobre o mapa natal. Cache recomendado: 24h."""
    try:
        result = calculate_transits(
            natal_chart=body.natal_chart,
            current_date=body.current_date,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro nos transitos: {str(e)}")


@app.post("/interpret-transits")
async def interpret_transits_endpoint(body: InterpretTransitsRequest):
    """Interpreta os transitos atuais com LLM."""
    try:
        tr    = body.transits_result
        chart = body.natal_chart
        name  = body.user_name
        pron  = pronouns(body.gender)
        today = tr.get("period", datetime.utcnow().strftime("%Y-%m-%d"))

        top_transits = tr.get("transits", [])[:8]
        transit_text = "\n".join([
            f"  {t['transitPlanet']} em {t['transitSign']} {t['symbol']} "
            f"{t['natalPlanet']} natal "
            f"({t['aspect']}, orbe {t['orb']:.1f}*{'R' if t.get('transitRetrograde') else ''})"
            for t in top_transits
        ])

        in_houses = tr.get("transitsInHouses", [])
        house_text = "\n".join([
            f"  {t['planet']} transitando Casa {t['house']} ({t['sign']})"
            for t in in_houses
        ])

        prompt = f"""{AURELIO_SYSTEM}

---

## ANALISE DE TRANSITOS -- {name.upper()}
**Data:** {today}

Sol natal: {chart.get('sun', '-')} | Lua natal: {chart.get('moon', '-')} | Ascendente natal: {chart.get('ascendant', '-')}

### Aspectos em Transito (mais significativos primeiro):
{transit_text if transit_text else "Nenhum transito maior ativo neste momento."}

### Planetas em Transito pelas Casas Natais:
{house_text if house_text else "-"}

---

Elabore uma analise profunda dos transitos atuais de {name}.

### Panorama do Periodo
Visao geral das energias predominantes. Qual e o tema central deste momento?

### Os 3 Transitos Mais Significativos
Para cada um: o que significa, como se manifesta na vida de {pron['subj']}, duracao aproximada.

### Orientacao Pratica
O que {pron['subj']} deve focar, cultivar, evitar ou aproveitar neste periodo especifico.

### Intensidade e Duracao
Quando esses transitos atingem o pico e quando aliviam. Ate quando este ciclo dura.

Escreva em portugues brasileiro. Seja especifico -- use as posicoes exatas."""

        result = await generate(prompt, temperature=0.75, max_tokens=2500)
        return {"interpretation": result, "period": today}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interpretando transitos: {str(e)}")


@app.post("/solar-return")
async def solar_return_endpoint(body: SolarReturnRequest):
    """Calcula a Revolucao Solar com precisao de segundos. Cache recomendado: 1 ano."""
    try:
        lat, lon, _ = await resolve_location(
            body.city, body.country, body.lat, body.lon, None
        )
        sr_chart = calculate_solar_return(
            natal_chart=body.natal_chart,
            birth_date=body.birth_date,
            birth_time=body.birth_time,
            lat=lat,
            lon=lon,
            year=body.year or datetime.utcnow().year,
        )
        return sr_chart
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na Revolucao Solar: {str(e)}")


@app.post("/interpret-solar")
async def interpret_solar_endpoint(body: InterpretSolarRequest):
    """Interpreta a Revolucao Solar com LLM."""
    try:
        sr    = body.solar_chart
        natal = body.natal_chart
        name  = body.user_name
        year  = body.year or sr.get("solarReturnYear", datetime.utcnow().year)
        pron  = pronouns(body.gender)

        sr_planets = [
            p for p in sr.get("planets", [])
            if p["name"] in {"Sol", "Lua", "Marte", "Jupiter", "Saturno"}
        ]
        sr_planet_text = "\n".join([
            f"  {p['name']} em {p['sign']}, Casa {p.get('house', '?')}"
            for p in sr_planets
        ])

        prompt = f"""{AURELIO_SYSTEM}

---

## REVOLUCAO SOLAR {year} -- {name.upper()}

Mapa Natal (base):
Sol: {natal.get('sun', '-')} | Lua: {natal.get('moon', '-')} | Asc: {natal.get('ascendant', '-')}

Revolucao Solar {year}:
Ascendente RS: {sr.get('ascendant', '-')} | MC RS: {sr.get('midheaven', '-')}
Momento exato: {sr.get('exactDatetimeUTC', '-')}

Planetas principais na RS:
{sr_planet_text}

---

Elabore uma **previsao profunda** para o ano pessoal {year}/{year + 1} de {name}.

### O Tema Central do Ano
Sintese do que este ciclo traz como proposta evolutiva central para {pron['art']} {name}.

### Casas Ativadas e Areas de Vida
Quais dominios (amor, carreira, saude, familia, espiritualidade) serao mais movimentados e por que.

### Janelas de Oportunidade
Onde o crescimento, a fortuna e a expansao estao disponiveis neste ciclo.

### Desafios e Trabalho Interior
O que exigira maturidade, paciencia e autoconhecimento de {pron['subj']}.

### Momentos de Maior Intensidade
Estacoes ou meses do ano onde as energias ficam mais intensas ou trazem viradas.

### Mensagem Espiritual
O que a alma de {name} esta sendo convidada a aprender neste ano.

Escreva em portugues brasileiro. Profundo, personalizado e baseado nos dados do mapa."""

        result = await generate(prompt, temperature=0.78, max_tokens=3000)
        return {"interpretation": result, "year": year}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interpretando RS: {str(e)}")


@app.post("/astrologo/chat")
async def astrologo_chat_endpoint(body: ChatRequest):
    """Chat com o Prof. Aurelio -- maximo 5 perguntas por sessao."""
    try:
        chart  = body.natal_chart
        name   = body.user_name
        pron   = pronouns(body.gender)
        q_left = body.questions_left

        quick_ctx = (
            f"Sol: {chart.get('sun', '-')} | Lua: {chart.get('moon', '-')} | "
            f"Asc: {chart.get('ascendant', '-')} | MC: {chart.get('midheaven', '-')}"
        )

        strong = [d for d in chart.get("dignities", []) if d.get("isStrong")]
        if strong:
            quick_ctx += "\nPlanetas em forca: " + ", ".join(
                f"{d['planet']} ({d['dignity']} em {d['sign']})" for d in strong
            )

        history_text = ""
        for msg in body.history[-6:]:
            role = name if msg.get("role") == "user" else "Prof. Aurelio"
            history_text += f"\n{role}: {msg.get('content', '')}\n"

        closing = (
            "\n\nEsta e a ultima pergunta desta sessao. "
            "Encerre com uma mensagem de orientacao especial e uma bencao."
            if q_left <= 1 else ""
        )

        prompt = f"""{AURELIO_SYSTEM}

---

Voce esta em **sessao privada** com {name}.

Mapa Natal de {name}:
{quick_ctx}

Perguntas restantes nesta sessao: {q_left}/5{closing}

---
{history_text}
{name}: {body.question}

Prof. Aurelio: (responda com profundidade psicologica e astrologica, maximo 350 palavras, use os dados do mapa)"""

        response = await generate(prompt, temperature=0.80, max_tokens=600)
        return {
            "response": response,
            "questionsLeft": max(0, q_left - 1),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no chat: {str(e)}")


@app.post("/ask")
async def ask_endpoint(body: AskRequest):
    """
    Q&A focado: responde UMA pergunta com base nos trechos do mapa já interpretado.
    NÃO roda pipeline de interpretação — só passa o prompt cirúrgico para o LLM.
    Custo mínimo: ~600 tokens de saída, sem Swiss Ephemeris, sem build_chart_context.
    """
    try:
        history_text = ""
        for msg in body.history[-4:]:
            role = body.user_name if msg.get("role") == "user" else "Prof. Aurélio"
            history_text += f"\n{role}: {msg.get('content', '')}\n"

        prompt = f"""{AURELIO_SYSTEM}

---

Você está em sessão de perguntas com {body.user_name}.

Os trechos abaixo foram extraídos da interpretação astrológica de {body.user_name} que você mesmo elaborou anteriormente:

---
{body.context}
---
{history_text}
{body.user_name} pergunta: {body.question}

Prof. Aurélio: (Responda DIRETAMENTE à pergunta citando planetas, casas e aspectos específicos do trecho acima. NÃO reescreva a interpretação completa. NÃO introduza a si mesmo. Máximo 3 parágrafos densos e pessoais.)"""

        result = await generate(prompt, temperature=0.78, max_tokens=600)
        return {"answer": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Q&A: {str(e)}")


@app.post("/astrum-interpret")
async def generic_interpret_endpoint(body: GenericPromptRequest):
    """Endpoint generico de fallback para o frontend."""
    try:
        result = await generate(body.prompt, temperature=0.78, max_tokens=4096)
        return {"interpretation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Desenvolvimento local ──────────────────────────────────────────────────────

# ── Aliases de compatibilidade com a API anterior do Railway ─────────────────
# O frontend ASTRUM chama /calculate-chart e /interpret-by-houses.
# Estes aliases traduzem o formato antigo para o novo.

class NewBirthData(BaseModel):
    name:   str = "Consultante"
    year:   int
    month:  int
    day:    int
    hour:   int
    minute: int
    city:   str
    nation: str = "BR"

class CalculateChartRequest(BaseModel):
    birth_data: NewBirthData
    objective:  str = ""

class InterpretByHousesRequest(BaseModel):
    birth_data: NewBirthData
    objective:  str = ""
    user_name:  Optional[str] = None

class InterpretTransitRequest(BaseModel):
    birth_data: NewBirthData
    objective:  str = ""
    user_name:  Optional[str] = None


@app.post("/calculate-chart")
async def calculate_chart_compat(body: CalculateChartRequest):
    """Alias compatível: converte payload novo → /natal-chart."""
    from datetime import date as _date
    bd = body.birth_data
    date_str = f"{bd.year:04d}-{bd.month:02d}-{bd.day:02d}"
    time_str = f"{bd.hour:02d}:{bd.minute:02d}"
    # Tenta geocodificar para obter lat/lon/tz
    try:
        lat, lon, tz = await geocode(bd.city, bd.nation)
    except Exception:
        lat, lon, tz = -23.55, -46.63, -3.0  # fallback São Paulo

    chart = calculate_chart(date_str, time_str, lat, lon, tz_offset=tz)
    # Adiciona campos extras que o frontend espera
    chart["birthCity"]    = bd.city
    chart["birthCountry"] = bd.nation
    chart["birthDate"]    = date_str
    chart["birthTime"]    = time_str
    chart["lat"]          = lat
    chart["lon"]          = lon
    chart["tz"]           = tz
    return chart


@app.post("/interpret-by-houses")
async def interpret_by_houses_compat(body: InterpretByHousesRequest):
    """Alias compatível: chama /interpret-natal com chart recalculado."""
    bd = body.birth_data
    name = body.user_name or bd.name
    date_str = f"{bd.year:04d}-{bd.month:02d}-{bd.day:02d}"
    time_str = f"{bd.hour:02d}:{bd.minute:02d}"

    try:
        lat, lon, tz = await geocode(bd.city, bd.nation)
    except Exception:
        lat, lon, tz = -23.55, -46.63, -3.0

    chart = calculate_chart(date_str, time_str, lat, lon, tz_offset=tz)
    context = build_chart_context(chart, include_aspects=True)

    # Reutiliza a mesma lógica do /interpret-natal (planeta a planeta)
    req = InterpretNatalRequest(chart=chart, user_name=name, gender="neutro")
    result = await interpret_natal_endpoint(req)
    interpretation = result["interpretation"]
    return {"interpretation": interpretation, "chart": chart}


@app.post("/interpret-transit")
async def interpret_transit_compat(body: InterpretTransitRequest):
    """Alias compatível para /interpret-transits."""
    bd = body.birth_data
    name = body.user_name or bd.name
    date_str = f"{bd.year:04d}-{bd.month:02d}-{bd.day:02d}"
    time_str = f"{bd.hour:02d}:{bd.minute:02d}"

    try:
        lat, lon, tz = await geocode(bd.city, bd.nation)
    except Exception:
        lat, lon, tz = -23.55, -46.63, -3.0

    natal = calculate_chart(date_str, time_str, lat, lon, tz_offset=tz)
    transit_result = calculate_transits(natal_chart=natal)
    context = build_chart_context(natal, include_aspects=False)

    prompt = f"""{AURELIO_SYSTEM}

---

## TRÂNSITOS ATUAIS — {name.upper()}

Mapa natal:
{context}

Trânsitos em atividade: {len(transit_result.get('transits', []))} aspectos ativos.

---

Elabore uma análise dos trânsitos atuais de {name}. Seja específico com as posições.
Use português brasileiro."""

    interpretation = await generate(prompt, temperature=0.75, max_tokens=2500)
    return {
        "interpretation": interpretation,
        "transits": transit_result,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)

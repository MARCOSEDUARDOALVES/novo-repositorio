"""
astrum_db.py — Banco de conhecimento astrológico ASTRUM
========================================================
Tabelas:
  planet_sign_keywords   → planetas x signos  (arquétipos, keywords, notas Jung/Freud)
  planet_house_keywords  → planetas x casas   (temas, dons, desafios)
  house_meanings         → as 12 casas        (área de vida, corpo, regente)
  aspect_meanings        → aspectos por par   (psicologia, keywords)
  knowledge_chunks       → trechos dos livros (RAG)
  user_charts            → cache de mapas calculados
  transit_cache          → cache de trânsitos (TTL 24 h)
  solar_return_cache     → cache de RS        (TTL 1 ano)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "astrum.db")


# ── Conexão ───────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── DDL ───────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS planet_sign_keywords (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    planet            TEXT NOT NULL,
    sign              TEXT NOT NULL,
    keywords          TEXT NOT NULL,       -- JSON array  (dons/positivo)
    shadow_keywords   TEXT,                -- JSON array  (sombra/desafio)
    jungian_archetype TEXT,
    jungian_notes     TEXT,
    freudian_note     TEXT,
    element           TEXT,
    modality          TEXT,
    ruling_planet     TEXT,
    body_part         TEXT,
    UNIQUE(planet, sign)
);

CREATE TABLE IF NOT EXISTS planet_house_keywords (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    planet      TEXT NOT NULL,
    house       INTEGER NOT NULL,
    theme       TEXT NOT NULL,
    keywords    TEXT NOT NULL,   -- JSON array
    gifts       TEXT,            -- JSON array
    challenges  TEXT,            -- JSON array
    life_area   TEXT,
    UNIQUE(planet, house)
);

CREATE TABLE IF NOT EXISTS house_meanings (
    house           INTEGER PRIMARY KEY,
    name_pt         TEXT NOT NULL,
    life_area       TEXT NOT NULL,
    body_part       TEXT,
    keywords        TEXT NOT NULL,   -- JSON array
    shadow          TEXT,            -- JSON array
    ruling_sign     TEXT,
    ruling_planet   TEXT,
    jungian_theme   TEXT,
    freudian_theme  TEXT,
    house_type      TEXT             -- Angular / Sucedente / Cadente
);

CREATE TABLE IF NOT EXISTS aspect_meanings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    planet_a      TEXT NOT NULL,
    planet_b      TEXT NOT NULL,
    aspect        TEXT NOT NULL,
    nature        TEXT NOT NULL,
    theme         TEXT,
    keywords      TEXT,            -- JSON array
    psychological TEXT,
    jungian_note  TEXT,
    UNIQUE(planet_a, planet_b, aspect)
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,
    chapter     TEXT,
    chunk_text  TEXT NOT NULL,
    embedding   TEXT,            -- JSON float array
    tags        TEXT,            -- JSON array
    created_at  INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS user_charts (
    uid           TEXT PRIMARY KEY,
    birth_date    TEXT NOT NULL,
    birth_time    TEXT NOT NULL,
    birth_city    TEXT NOT NULL,
    birth_country TEXT,
    lat           REAL,
    lon           REAL,
    chart_json    TEXT NOT NULL,
    calculated_at INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS transit_cache (
    uid         TEXT NOT NULL,
    date        TEXT NOT NULL,
    result_json TEXT NOT NULL,
    cached_at   INTEGER DEFAULT (strftime('%s','now')),
    PRIMARY KEY (uid, date)
);

CREATE TABLE IF NOT EXISTS solar_return_cache (
    uid         TEXT NOT NULL,
    year        INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    cached_at   INTEGER DEFAULT (strftime('%s','now')),
    PRIMARY KEY (uid, year)
);
"""


def init_db() -> None:
    """Cria todas as tabelas se não existirem."""
    conn = get_conn()
    conn.executescript(_DDL)
    conn.commit()
    conn.close()


# ── Dados: Casas ──────────────────────────────────────────────────────────────

_HOUSES: list[tuple] = [
    (1,  "Casa do Self",          "Identidade, aparencia, primeiras impressoes",
     "Cabeca, rosto",
     ["eu","corpo","aparencia","inicio","vitalidade","persona"],
     ["egocentrismo","vaidade"],
     "Aries","Marte",
     "Persona — mascara social (Jung)",
     "Ego — estrutura do self consciente (Freud)",
     "Angular"),
    (2,  "Casa dos Recursos",     "Dinheiro, posses, valores pessoais",
     "Pescoco, garganta",
     ["dinheiro","valores","seguranca","talentos","autoestima"],
     ["apego material","avareza"],
     "Touro","Venus",
     "Self material — o que valorizamos define quem somos",
     "Fixacao oral — seguranca primitiva",
     "Sucedente"),
    (3,  "Casa da Comunicacao",   "Irmaos, vizinhanca, mente concreta, viagens curtas",
     "Bracos, maos, pulmoes",
     ["comunicacao","aprendizado","irmaos","escrita","curiosidade"],
     ["dispersao","superficialidade"],
     "Gemeos","Mercurio",
     "Trickster — o comunicador travesso",
     "Sublimacao via linguagem",
     "Cadente"),
    (4,  "Fundo do Ceu / Raizes", "Lar, familia, ancestralidade, base emocional",
     "Peito, estomago",
     ["familia","lar","raizes","inconsciente profundo","mae"],
     ["apego ao passado","complexo materno"],
     "Cancer","Lua",
     "Grande Mae — arquetipo materno e da alma",
     "Complexo materno — Freud/Jung",
     "Angular"),
    (5,  "Casa da Criatividade",  "Amor, filhos, prazer, autoexpressao, arte",
     "Coracao, coluna",
     ["criatividade","amor","prazer","filhos","jogo","romance"],
     ["hedonismo","narcisismo"],
     "Leao","Sol",
     "Crianca Interior — expressao pura do ser",
     "Principio do prazer — Eros",
     "Sucedente"),
    (6,  "Casa do Servico",       "Trabalho diario, saude, rotina, servidores",
     "Intestinos, sistema digestivo",
     ["saude","rotina","servico","trabalho","corpo"],
     ["hipocondria","servidao","perfeccionismo"],
     "Virgem","Mercurio",
     "O Servo — integracao da sombra pelo trabalho",
     "Neurose obsessiva — Freud",
     "Cadente"),
    (7,  "Casa das Parcerias",    "Casamento, contratos, parcerias, inimigos declarados",
     "Rins, ossos do quadril",
     ["parceria","casamento","outro","contratos","projecao"],
     ["dependencia","projecao da sombra"],
     "Libra","Venus",
     "Anima/Animus — o outro como espelho da alma",
     "Transferencia — repeticao de padroes afetivos",
     "Angular"),
    (8,  "Casa da Transformacao", "Morte, sexo, herancas, transformacao profunda, oculto",
     "Orgaos reprodutores, intestino grosso",
     ["transformacao","morte","renascimento","sexo","poder","oculto"],
     ["obsessao","controle","destruicao"],
     "Escorpiao","Plutao",
     "Sombra — o que esta escondido nas trevas da psique",
     "Instinto de morte — Tanatos",
     "Sucedente"),
    (9,  "Casa da Filosofia",     "Religiao, filosofia, viagens longas, ensino superior",
     "Coxas, figado",
     ["filosofia","religiao","viagem","expansao","sabedoria","lei"],
     ["dogmatismo","escapismo","fanatismo"],
     "Sagitario","Jupiter",
     "Sabio/Mago — a busca pelo sentido",
     "Sublimacao espiritual",
     "Cadente"),
    (10, "Meio do Ceu / Carreira","Carreira, reputacao, pai, autoridade, destino publico",
     "Joelhos, ossos, estrutura",
     ["carreira","reputacao","status","missao","pai","autoridade"],
     ["ambicao excessiva","complexo paterno"],
     "Capricornio","Saturno",
     "Velho Sabio — autoridade e estrutura",
     "Complexo paterno — Superego",
     "Angular"),
    (11, "Casa das Redes",        "Amizades, grupos, ideais, humanitarismo, futuro",
     "Tornozelos, circulacao",
     ["amizades","grupos","ideais","humanitarismo","futuro","comunidade"],
     ["utopismo","rebeldia","dispersao"],
     "Aquario","Urano",
     "Heroi coletivo — o individuo a servico do todo",
     "Sublimacao social",
     "Sucedente"),
    (12, "Casa do Inconsciente",  "Isolamento, karma, espiritualidade, sacrificio",
     "Pes, sistema linfatico",
     ["inconsciente","karma","retiro","espiritualidade","sacrificio","dissolucao"],
     ["autossabotagem","fuga da realidade","vitimismo"],
     "Peixes","Netuno",
     "A Sombra coletiva — o que negamos em nos",
     "Inconsciente — repressao profunda",
     "Cadente"),
]


def _seed_houses(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO house_meanings
           (house, name_pt, life_area, body_part, keywords, shadow,
            ruling_sign, ruling_planet, jungian_theme, freudian_theme, house_type)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (h[0], h[1], h[2], h[3],
             json.dumps(h[4], ensure_ascii=False),
             json.dumps(h[5], ensure_ascii=False),
             h[6], h[7], h[8], h[9], h[10])
            for h in _HOUSES
        ],
    )


# ── Dados: Planetas × Signos ─────────────────────────────────────────────────
# Formato: (planet, sign, keywords+, keywords-, arquétipo, notas_jung, notas_freud, elem, modal, regente, corpo)

_PLANET_SIGNS: list[tuple] = [
    # ── SOL × 12 SIGNOS ──────────────────────────────────────────────────────
    ("Sol","Aries",
     ["lideranca","coragem","pioneirismo","autonomia"],
     ["impulsividade","arrogancia","impaciencia"],
     "Heroi/Guerreiro",
     "O Heroi que age antes de pensar — arquetipo do iniciador",
     "Ego dominado pelo Id — energia pulsional nao mediada pelo principio de realidade",
     "Fogo","Cardinal","Marte","Cabeca"),
    ("Sol","Touro",
     ["estabilidade","sensualidade","persistencia","producao"],
     ["teimosia","possessividade","materialismo"],
     "Construtor/Rei",
     "O Construtor que transforma recursos em permanencia — seguranca material como expressao do self",
     "Regressao oral — necessidade de segurar o valioso como defesa contra a perda",
     "Terra","Fixo","Venus","Garganta"),
    ("Sol","Gemeos",
     ["inteligencia","versatilidade","comunicacao","curiosidade"],
     ["superficialidade","inconstancia","duplicidade"],
     "Trickster/Mensageiro",
     "O Trickster que danca entre polaridades — a mente como identidade",
     "Intelectualizacao — distancia emocional como defesa",
     "Ar","Mutavel","Mercurio","Pulmoes"),
    ("Sol","Cancer",
     ["sensibilidade","nutricao","intuicao","memoria emocional"],
     ["dependencia emocional","ressentimento","apego ao passado"],
     "Grande Mae/Nutrix",
     "O Self que se expressa pelo cuidado — identidade fundada na pertenca e nas raizes",
     "Complexo materno — self organizado em torno da fusao/separacao com a mae",
     "Agua","Cardinal","Lua","Peito"),
    ("Sol","Leao",
     ["criatividade","lideranca","generosidade","nobreza"],
     ["narcisismo","autoritarismo","necessidade de aprovacao"],
     "Rei/Heroi Solar",
     "O Rei — expressao maxima do arquetipo solar; o self que precisa brilhar para existir",
     "Narcisismo primario — necessidade de espelhamento e reconhecimento",
     "Fogo","Fixo","Sol","Coracao"),
    ("Sol","Virgem",
     ["discernimento","servico","analise","perfeicao"],
     ["hipercriticismo","ansiedade","excesso de autocritica"],
     "O Servo/O Eremita",
     "O Eremita que busca aperfeicoamento — o self como processo de refinamento constante",
     "Neurose obsessiva — compulsao por ordem como defesa contra o caos interno",
     "Terra","Mutavel","Mercurio","Intestinos"),
    ("Sol","Libra",
     ["equilibrio","diplomacia","senso estetico","justica"],
     ["indecisao","dependencia do outro","evitacao de conflito"],
     "O Amante/O Juiz",
     "O Amante que se descobre pelo outro — identidade construida na relacao",
     "Negacao — dificuldade em reconhecer a propria sombra agressiva",
     "Ar","Cardinal","Venus","Rins"),
    ("Sol","Escorpiao",
     ["intensidade","profundidade","poder de transformacao","resiliencia"],
     ["obsessao","ciumo","manipulacao","destrutividade"],
     "Fenix/Plutao",
     "A Fenix — o self que so se encontra passando pela morte simbolica",
     "Instinto de morte (Tanatos) integrado ao Eros — pulsao destrutiva a servico da criacao",
     "Agua","Fixo","Plutao","Genitais"),
    ("Sol","Sagitario",
     ["expansao","otimismo","sabedoria","aventura","fe"],
     ["excesso","irresponsabilidade","dogmatismo"],
     "O Explorador/O Profeta",
     "O Explorador de Mundos — o self que so existe em movimento, buscando o horizonte",
     "Sublimacao das pulsoes pela filosofia e busca espiritual",
     "Fogo","Mutavel","Jupiter","Coxas"),
    ("Sol","Capricornio",
     ["ambicao","disciplina","responsabilidade","autoridade"],
     ["rigidez","frieza afetiva","workaholic","pessimismo"],
     "O Velho Sabio/Saturno",
     "O Velho Sabio que constroi pelo tempo — identidade forjada no trabalho e na superacao",
     "Superego hipertrofiado — autoexigencia extrema como internalizacao da figura paterna severa",
     "Terra","Cardinal","Saturno","Joelhos"),
    ("Sol","Aquario",
     ["originalidade","humanitarismo","liberdade","inovacao"],
     ["desapego emocional","rebeldia","excesso de racionalizacao"],
     "O Rebelde/Prometeu",
     "Prometeu — aquele que rouba o fogo dos deuses para dar a humanidade; o self como missao coletiva",
     "Sublimacao intelectual — distancia afetiva como protecao do ego",
     "Ar","Fixo","Urano","Tornozelos"),
    ("Sol","Peixes",
     ["compaixao","espiritualidade","imaginacao","empatia"],
     ["confusao de limites","escapismo","vitimismo","autossacrificio excessivo"],
     "O Mistico/Cristo",
     "O Mistico — dissolucao do ego como caminho espiritual; o self que se funde com o todo",
     "Regressao oceanica — desejo de retorno ao estado pre-natal de fusao com o tudo",
     "Agua","Mutavel","Netuno","Pes"),

    # ── LUA × 12 SIGNOS ──────────────────────────────────────────────────────
    ("Lua","Aries",
     ["reatividade emocional","espontaneidade","coragem afetiva","independencia"],
     ["impaciencia emocional","reacoes explosivas","dificuldade de aconchego"],
     "Amazona",
     "Anima guerreira — a alma que se move por impulso e precisa de autonomia emocional",
     "Libido emotiva nao mediada — resposta instintiva direta",
     "Fogo","Cardinal","Marte","Cabeca"),
    ("Lua","Touro",
     ["seguranca emocional","constancia","amor sensorial","nutricao pelo tato"],
     ["possessividade emocional","resistencia a mudanca","apego ao conforto"],
     "A Provedora",
     "Anima materializadora — a alma que encontra paz no que pode tocar e sentir",
     "Fixacao oral satisfeita — mundo emocional organizado em torno do prazer sensorial seguro",
     "Terra","Fixo","Venus","Garganta"),
    ("Lua","Gemeos",
     ["inteligencia emocional","necessidade de variedade","sociabilidade afetiva"],
     ["ansiedade emocional","racionalizacao dos sentimentos","inconstancia afetiva"],
     "A Musa",
     "Anima comunicadora — a alma que processa emocoes por palavras e ideias",
     "Intelectualizacao como defesa — transformar sentimentos em conceitos para controla-los",
     "Ar","Mutavel","Mercurio","Pulmoes"),
    ("Lua","Cancer",
     ["profunda sensibilidade","memoria emocional vivida","intuicao","instinto materno"],
     ["hipersensibilidade","apego ao passado","dificuldade em deixar ir"],
     "Grande Mae",
     "Anima em sua forma mais pura — o inconsciente como oceano de memoria e sentimento",
     "Complexo materno central — toda a vida emocional em torno da relacao com o materno",
     "Agua","Cardinal","Lua","Peito"),
    ("Lua","Leao",
     ["generosidade afetiva","expressao emocional dramatica","calor humano","lealdade"],
     ["necessidade excessiva de reconhecimento emocional","drama","orgulho ferido"],
     "A Rainha",
     "Anima regia — a alma que precisa ser vista e celebrada em sua beleza",
     "Narcisismo afetivo — necessidade de espelhamento emocional como condicao de bem-estar",
     "Fogo","Fixo","Sol","Coracao"),
    ("Lua","Virgem",
     ["cuidado pratico","atencao aos detalhes afetivos","servico como amor"],
     ["hipercriticismo emocional","ansiedade de saude","dificuldade em receber cuidado"],
     "A Curandeira",
     "Anima purificadora — a alma que expressa amor pelo cuidado concreto e pelo servico",
     "Formacao reativa — substituicao de pulsoes agressivas por servilidade e cuidado compulsivo",
     "Terra","Mutavel","Mercurio","Intestinos"),
    ("Lua","Libra",
     ["necessidade de harmonia","afeto refinado","beleza como nutricao emocional"],
     ["dificuldade com emocoes intensas","dependencia afetiva","negacao do conflito interno"],
     "A Mediadora",
     "Anima harmonica — a alma que so se sente bem em equilibrio e beleza relacional",
     "Negacao — impossibilidade de tolerar o feio e o conflituoso no campo emocional",
     "Ar","Cardinal","Venus","Rins"),
    ("Lua","Escorpiao",
     ["intensidade emocional","lealdade profunda","intuicao psiquica","resiliencia"],
     ["ciumo patologico","rancor","manipulacao afetiva"],
     "A Feiticeira",
     "Anima ctonicas — a alma mergulhada nas profundezas do inconsciente; amor como fogo que transforma",
     "Ambivalencia amor-odio — fusao de Eros e Tanatos na vida emocional",
     "Agua","Fixo","Plutao","Genitais"),
    ("Lua","Sagitario",
     ["otimismo emocional","necessidade de liberdade afetiva","entusiasmo","fe"],
     ["fugir de intimidade profunda","superficialidade emocional","irresponsabilidade afetiva"],
     "A Xama",
     "Anima peregrina — a alma que precisa de horizonte e nao suporta clausura emocional",
     "Sublimacao — transformacao da dor emocional em busca filosofica ou espiritual",
     "Fogo","Mutavel","Jupiter","Coxas"),
    ("Lua","Capricornio",
     ["autocontrole emocional","responsabilidade afetiva","amor duradouro e leal"],
     ["repressao emocional","frieza aparente","dificuldade em pedir ajuda"],
     "A Ancia",
     "Anima saturnina — a alma que aprendeu que sentir e perigoso; protecao pelo controle",
     "Repressao classica — supressao das emocoes vulneraveis como resposta a ambiente parental austero",
     "Terra","Cardinal","Saturno","Joelhos"),
    ("Lua","Aquario",
     ["afeto universal","liberdade emocional","originalidade afetiva"],
     ["distancia emocional","racionalizacao do sentimento","medo de intimidade"],
     "A Visionaria",
     "Anima coletiva — a alma que se emociona com a humanidade mas resiste a vulnerabilidade individual",
     "Intelectualizacao radical — mundo emocional filtrado completamente pela razao",
     "Ar","Fixo","Urano","Tornozelos"),
    ("Lua","Peixes",
     ["empatia profunda","amor incondicional","imaginacao emocional vivida"],
     ["fusao com o outro","dificuldade de limites","hipersensibilidade ao sofrimento alheio"],
     "A Sacerdotisa",
     "Anima mistica — a alma porosa que absorve tudo ao redor; inconsciente sem bordas definidas",
     "Regressao oceanica — dissolucao do ego no campo emocional como busca de fusao primitiva",
     "Agua","Mutavel","Netuno","Pes"),

    # ── MERCURIO × 12 SIGNOS ─────────────────────────────────────────────────
    ("Mercurio","Aries",
     ["pensamento rapido","direto","assertivo","pioneiro"],
     ["impulsividade verbal","precipitacao","intolerancia"],
     "O Mensageiro Guerreiro",
     "Mente que age antes de pensar — a palavra como espada",
     "Processo primario na comunicacao — o impulso sobrepoe a reflexao",
     "Fogo","Cardinal","Marte","Cabeca"),
    ("Mercurio","Touro",
     ["pensamento concreto","methodico","memoriavisual forte","pratico"],
     ["lentidao para mudar de ideia","teimosia mental","resistencia ao novo"],
     "O Arquiteto",
     "Mente que constroi — o pensamento precisa de base solida e tempo para amadurecer",
     "Prazer na aquisicao do conhecimento — aprender e uma forma de posse",
     "Terra","Fixo","Venus","Garganta"),
    ("Mercurio","Gemeos",
     ["rapidez mental","versatilidade","habilidade linguistica","curiosidade insaciavel"],
     ["superficialidade","ansiedade mental","dificuldade de foco"],
     "O Trickster/Hermes",
     "Mente no seu domicilio — o Trickster em casa; pensamento e brincadeira sao a mesma coisa",
     "Funcionamento do processo secundario em alta rotacao — a mente como defesa",
     "Ar","Mutavel","Mercurio","Pulmoes"),
    ("Mercurio","Cancer",
     ["memoria afetiva","intuicao","pensamento associativo","empatia cognitiva"],
     ["racionalizar emocoes","subjetividade excessiva","dificuldade de objetividade"],
     "O Arquivista da Alma",
     "Mente que sente — o pensamento mediado pela emocao e pela memoria ancestral",
     "O inconsciente informa o consciente — pensamento tingido de afeto",
     "Agua","Cardinal","Lua","Peito"),
    ("Mercurio","Leao",
     ["expressao dramatica","narrativa criativa","lideranca comunicativa","carisma verbal"],
     ["orgulho intelectual","necessidade de audiencia","exagero"],
     "O Contador de Historias",
     "Mente que performa — o pensamento como expressao do self glorioso",
     "Narcisismo cognitivo — as proprias ideias como objeto de amor",
     "Fogo","Fixo","Sol","Coracao"),
    ("Mercurio","Virgem",
     ["analise precisa","discernimento fino","pensamento critico","praticidade"],
     ["hipercriticismo","preocupacao excessiva","paralisia por analise"],
     "O Analista",
     "Mente em exaltacao — o pensamento a servico do aperfeicoamento e da utilidade",
     "Formacao reativa intelectual — a critica como defesa contra o caos",
     "Terra","Mutavel","Mercurio","Intestinos"),
    ("Mercurio","Libra",
     ["pensamento diplomatico","ponderacao","estetica nas ideias","mediacao"],
     ["indecisao","procrastinacao mental","evitar confronto intelectual"],
     "O Diplomata",
     "Mente que pondera — o pensamento busca sempre o ponto de equilibrio e a visao do outro",
     "Formacao reativa — evitar o pensamento agressivo atraves da diplomacia",
     "Ar","Cardinal","Venus","Rins"),
    ("Mercurio","Escorpiao",
     ["penetracao psicologica","investigacao","pensamento estrategico","percepcao profunda"],
     ["desconfianca","pensamento obsessivo","uso manipulador da informacao"],
     "O Investigador",
     "Mente que vasculha o inconsciente — o pensamento como ferramenta de transformacao",
     "Pulsao epistemica — necessidade de saber tudo como controle da ansiedade",
     "Agua","Fixo","Plutao","Genitais"),
    ("Mercurio","Sagitario",
     ["visao global","pensamento filosofico","otimismo cognitivo","intuicao expansiva"],
     ["falta de atencao ao detalhe","exagero","dogmatismo","superficialidade"],
     "O Filosofo",
     "Mente que busca o horizonte — o pensamento como viagem em busca de sentido",
     "Sublimacao intelectual — o desejo tranformado em busca de significado universal",
     "Fogo","Mutavel","Jupiter","Coxas"),
    ("Mercurio","Capricornio",
     ["pensamento estruturado","disciplina mental","planejamento","pragmatismo"],
     ["rigidez cognitiva","pessimismo","lentidao para ideias novas"],
     "O Estrategista",
     "Mente que planeja pelo tempo — o pensamento a servico do objetivo de longo prazo",
     "Superego cognitivo — a critica interna nunca descansa",
     "Terra","Cardinal","Saturno","Joelhos"),
    ("Mercurio","Aquario",
     ["pensamento inovador","originalidade","visao futurista","logica sistemica"],
     ["desapego emocional nas ideias","intelectualizacao excessiva","teimosia"],
     "O Visionario",
     "Mente que voa — o pensamento como instrumento de ruptura com o estabelecido",
     "Sublimacao radical — toda pulsao transformada em conceito ou sistema",
     "Ar","Fixo","Urano","Tornozelos"),
    ("Mercurio","Peixes",
     ["imaginacao criativa","pensamento simbolico","intuicao poetica","empatia cognitiva"],
     ["confusao mental","dificuldade de foco","escapismo cognitivo"],
     "O Poeta/O Vidente",
     "Mente que sonha — o pensamento como portal entre o consciente e o inconsciente",
     "Processo primario predominante — o sonho contamina o pensamento acordado",
     "Agua","Mutavel","Netuno","Pes"),

    # ── VENUS × 12 SIGNOS ────────────────────────────────────────────────────
    ("Venus","Aries",
     ["amor direto","paixao imediata","coragem afetiva","seducao assertiva"],
     ["impaciencia no amor","impulsividade afetiva","conflito como coqueteria"],
     "A Guerreira Apaixonada",
     "Anima/Amor em modo de conquista — o amor como acao direta e imediata",
     "Principio do prazer imediato — Eros sem demora",
     "Fogo","Cardinal","Marte","Cabeca"),
    ("Venus","Touro",
     ["amor sensual","lealdade profunda","prazer nos sentidos","estetica refinada"],
     ["possessividade","ciume","resistencia ao fim de relacoes"],
     "A Sacerdotisa do Prazer",
     "Anima em domicilio — o amor como prazer sensorial, seguranca e permanencia",
     "Fixacao oral de amor — o afeto como nutricao e prazer dos sentidos",
     "Terra","Fixo","Venus","Garganta"),
    ("Venus","Gemeos",
     ["charme verbal","amor intelectual","versatilidade afetiva","leveza"],
     ["inconstancia afetiva","superficialidade emocional","dificuldade de comprometimento"],
     "A Musa Dualistia",
     "Anima comunicadora — o amor como troca intelectual e jogo de ideias",
     "Amor como estimulacao cognitiva — o parceiro deve alimentar a mente",
     "Ar","Mutavel","Mercurio","Pulmoes"),
    ("Venus","Cancer",
     ["amor nutridor","lealdade profunda","romantismo","senso de lar"],
     ["dependencia emocional","apego excessivo","ciumo encoberto"],
     "A Mae Amorosa",
     "Anima maternal — o amor como cuidado, protecao e pertenca ao lar",
     "Amor como nutricao — Eros mediado pela necessidade de cuidar e ser cuidado",
     "Agua","Cardinal","Lua","Peito"),
    ("Venus","Leao",
     ["amor generoso","criatividade afetiva","lealdade","romance grandioso"],
     ["necessidade excessiva de admiracao","ciume do orgulho","drama afetivo"],
     "A Rainha do Coracao",
     "Anima regia — o amor como palco de expressao do self; querer ser celebrado no amor",
     "Narcisismo afetivo — o amado como extensao do ego grandioso",
     "Fogo","Fixo","Sol","Coracao"),
    ("Venus","Virgem",
     ["amor pratico","servico como afeto","atencao aos detalhes do parceiro","fidelidade"],
     ["hipercriticismo no amor","autocritica afetiva","dificuldade de se entregar"],
     "A Curandeira do Amor",
     "Anima purificadora — o amor como dedicacao pratica e atencao refinada",
     "Amor como cuidado obsessivo — Eros mediado pelo servico e pela perfeicao",
     "Terra","Mutavel","Mercurio","Intestinos"),
    ("Venus","Libra",
     ["amor harmonioso","estetica afetiva","diplomacia","parceria equanime"],
     ["dependencia afetiva","indecisao no amor","evitacao de conflito"],
     "A Deusa do Equilibrio",
     "Anima em domicilio — o amor como parceria perfeita, belo equilibrio e troca justa",
     "O amor como espelho do ego ideal — o parceiro representa o que eu quero ser",
     "Ar","Cardinal","Venus","Rins"),
    ("Venus","Escorpiao",
     ["amor profundo","intensidade afetiva","lealdade feroz","transformacao pelo amor"],
     ["ciumo obsessivo","possessividade","poder e controle nas relacoes"],
     "A Feiticeira Apaixonada",
     "Anima ctonicas — o amor como descida ao submundo; quem ama transforma e e transformado",
     "Eros e Tanatos unidos — a pulsao amorosa carrega a sombra da destruicao",
     "Agua","Fixo","Plutao","Genitais"),
    ("Venus","Sagitario",
     ["amor livre","aventura afetiva","romance filosofico","generosidade"],
     ["medo de compromisso","infidelidade pelo tedio","exagero afetivo"],
     "A Aventureira do Amor",
     "Anima peregrina — o amor como expansao de horizontes; o parceiro como mestre ou companheiro de viagem",
     "Sublimacao de Eros — amor como busca de sentido e crescimento",
     "Fogo","Mutavel","Jupiter","Coxas"),
    ("Venus","Capricornio",
     ["amor duradouro","lealdade pratica","amor que constroi","comprometimento serio"],
     ["frieza afetiva aparente","amor transacional","dificuldade de expressao emocional"],
     "A Arquiteta do Amor",
     "Anima saturnina — o amor como construcao, responsabilidade e prova do tempo",
     "Amor como investimento — Eros mediado pelo principio de realidade",
     "Terra","Cardinal","Saturno","Joelhos"),
    ("Venus","Aquario",
     ["amor incondicional universal","amizade no amor","originalidade afetiva","liberdade"],
     ["distancia emocional","medo de intimidade real","amor intelectualizado"],
     "A Visionaria do Amor",
     "Anima coletiva — o amor como ideal humanitario; o parceiro como companheiro de causa",
     "Amor dessexualizado — Eros transformado em afeto universal e amizade",
     "Ar","Fixo","Urano","Tornozelos"),
    ("Venus","Peixes",
     ["amor incondicional","romantismo poetico","empatia profunda","amor espiritualizado"],
     ["fusao com o outro","ilusao afetiva","vitimismo no amor","autossacrificio"],
     "A Sacerdotisa do Amor Mistico",
     "Anima mistica — o amor como dissolucao dos limites entre eu e outro; Eros espiritualizado",
     "Regressao por amor — desejo de fusao total com o outro como repeticao do estado pre-natal",
     "Agua","Mutavel","Netuno","Pes"),

    # ── MARTE × 12 SIGNOS ────────────────────────────────────────────────────
    ("Marte","Aries",
     ["acao direta","coragem","energia vital abundante","lideranca"],
     ["agressividade","impulsividade","conflito por habito"],
     "O Guerreiro",
     "Marte em domicilio — o guerreiro que age por instinto puro, sem mediacao",
     "Id em acao — a energia libidinal em sua forma mais bruta e direta",
     "Fogo","Cardinal","Marte","Cabeca"),
    ("Marte","Touro",
     ["persistencia","forca constante","praticidade na acao","resistencia"],
     ["teimosia extrema","explosao quando no limite","possessividade agressiva"],
     "O Construtor Implacavel",
     "Marte que constroi devagar mas com forca irresistivel — a acao mediada pela materia",
     "Pulsao de vida canalizada para a producao material",
     "Terra","Fixo","Venus","Garganta"),
    ("Marte","Gemeos",
     ["agilidade","versatilidade na acao","debate","energia mental"],
     ["dispersao","superficialidade na acao","conflito verbal"],
     "O Espadachim das Palavras",
     "Marte que luta com a mente — a agressividade canalizada para o debate e a argumentacao",
     "Agressividade sublimada em argucia verbal",
     "Ar","Mutavel","Mercurio","Pulmoes"),
    ("Marte","Cancer",
     ["protecao feroz de quem ama","acao intuitiva","coragem emocional"],
     ["agressividade passiva","reatividade emocional","guardiar obsessivo"],
     "O Guerreiro da Familia",
     "Marte que protege o lar — a acao motivada pelo amor e pela seguranca afetiva",
     "Agressividade mediada pelo afeto — o instinto de morte a servico do instinto de vida",
     "Agua","Cardinal","Lua","Peito"),
    ("Marte","Leao",
     ["acao heroica","lideranca natural","coragem dramatica","criatividade assertiva"],
     ["arrogancia","drama no conflito","ego na acao"],
     "O Rei Guerreiro",
     "Marte que performa — a acao como expressao do self grandioso; o heroi que precisa de audiencia",
     "Id a servico do narcisismo — o ato heroico como confirmacao de grandiosidade",
     "Fogo","Fixo","Sol","Coracao"),
    ("Marte","Virgem",
     ["acao precisa","eficiencia","trabalho dedicado","critica construtiva"],
     ["critica obsessiva","ansiedade pela acao perfeita","servilidade agressiva"],
     "O Artesao Preciso",
     "Marte que aperfecoa — a energia vital canalizada para o servico e a excelencia",
     "Pulsao de morte sublimada em perfeicao — destruir o imperfeito para criar o excelente",
     "Terra","Mutavel","Mercurio","Intestinos"),
    ("Marte","Libra",
     ["acao diplomatica","justica como motivacao","assertividade elegante"],
     ["indecisao na acao","agressividade passiva","conflito por equidade"],
     "O Cavaleiro da Justica",
     "Marte em exilio — o guerreiro que nao consegue agir sem antes pesar todos os lados",
     "Agressividade negada e projetada — o conflito sempre vem 'de fora'",
     "Ar","Cardinal","Venus","Rins"),
    ("Marte","Escorpiao",
     ["determinacao implacavel","estrategia","resistencia","transformacao pela acao"],
     ["vinganca","manipulacao","obsessao","destruicao dos inimigos"],
     "O Feiticeiro Guerreiro",
     "Marte em domicilio — o guerreiro que conhece as sombras; a acao como transformacao profunda",
     "Fusao maxima de Eros e Tanatos — a pulsao de morte em servico da pulsao de vida",
     "Agua","Fixo","Plutao","Genitais"),
    ("Marte","Sagitario",
     ["acao expansiva","entusiasmo","aventura","coragem filosofica"],
     ["excesso de energia","falta de planejamento","cruzados fanticos"],
     "O Aventureiro Heroico",
     "Marte que explora — a acao motivada pela busca de sentido e pela expansao de horizontes",
     "Sublimacao da agressividade em missao e cruzada",
     "Fogo","Mutavel","Jupiter","Coxas"),
    ("Marte","Capricornio",
     ["disciplina de ferro","ambicao realizada","acao estrategica","autoridade"],
     ["frieza na acao","ambicao sem etica","workaholism"],
     "O General",
     "Marte em exaltacao — o guerreiro que planeja e constroi pelo tempo; disciplina como arma",
     "Pulsao de vida canalizada para o poder e a realizacao no mundo",
     "Terra","Cardinal","Saturno","Joelhos"),
    ("Marte","Aquario",
     ["acao coletiva","inovacao pela acao","rebeldia construtiva","original"],
     ["teimosia na acao","rebeldia por principio","frieza na luta"],
     "O Revolucionario",
     "Marte que revoluta — a acao motivada pela mudanca do sistema e pelo ideal coletivo",
     "Agressividade sublimada em revolta social construtiva",
     "Ar","Fixo","Urano","Tornozelos"),
    ("Marte","Peixes",
     ["acao intuitiva","compassivo na luta","arte como acao","sacrificio ativo"],
     ["dispersao na acao","escapismo antes da acao","martir agressivo"],
     "O Guerreiro Mistico",
     "Marte que dissolve — a acao motivada pela empatia e pelo sacrificio; o heroi que luta pela alma",
     "Pulsao de vida e morte dissoltas — dificuldade de separar a propria vontade da vontade do outro",
     "Agua","Mutavel","Netuno","Pes"),
]


def _seed_planet_signs(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO planet_sign_keywords
           (planet, sign, keywords, shadow_keywords, jungian_archetype,
            jungian_notes, freudian_note, element, modality, ruling_planet, body_part)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (r[0], r[1],
             json.dumps(r[2], ensure_ascii=False),
             json.dumps(r[3], ensure_ascii=False),
             r[4], r[5], r[6], r[7], r[8], r[9], r[10])
            for r in _PLANET_SIGNS
        ],
    )


# ── Dados: Aspectos ───────────────────────────────────────────────────────────

_ASPECTS: list[tuple] = [
    ("Sol","Lua","conjuncao","fusion",
     "Fusao de identidade e emocao",
     ["integracao","proposito alinhado ao sentimento","personalidade coesa"],
     "Sol (ego consciente) e Lua (inconsciente emocional) como uma unidade. Rara integracao do Self (Jung). Ego e Id em alinhamento (Freud).",
     "Coincidentia oppositorum — os opostos masculino/feminino unificados"),
    ("Sol","Lua","oposicao","tension",
     "Tensao entre identidade e necessidade emocional",
     ["conflito razao-sentimento","polarizacao","projecao no parceiro"],
     "O que voce e diverge do que voce sente. O trabalho de integrar a Sombra emocional (Jung). Conflito Ego/Id (Freud).",
     "Hieros gamos — o casamento sagrado como tarefa de integracao"),
    ("Sol","Lua","trigono","flow",
     "Harmonia entre ser e sentir",
     ["fluidez emocional","autoexpressao natural","empatia com proposito"],
     "O ego flui com o mundo emocional — querer e sentir alinhados. Facilita a individuacao.",
     "Ego e Id em cooperacao — satisfacao sem conflito significativo"),
    ("Sol","Lua","quadratura","challenge",
     "Friccao interna entre querer e sentir",
     ["tensao criativa","integracao dos opostos","crescimento pelo conflito"],
     "A tensao entre os opostos gera energia para a individuacao (Jung). Conflito intrapsiquico estrutural (Freud).",
     "A coniunctio que exige esforco — nunca resolucao facil"),
    ("Sol","Saturno","conjuncao","tension",
     "Identidade moldada pelo dever e pela disciplina",
     ["responsabilidade","maturidade precoce","autoridade conquistada"],
     "O Self em contato com o Velho Sabio — sabedoria pela provacao. Superego hipertrofiado (Freud).",
     "Puer e Senex unidos — o jovem que carrega o velho desde cedo"),
    ("Sol","Saturno","oposicao","tension",
     "Tensao entre brilho pessoal e limitacoes impostas",
     ["autoridade externa que bloqueia","medo de fracasso","crescimento pela superacao"],
     "O Velho Sabio como oponente externo que, integrado, torna-se sabedoria.",
     "Conflito Ego/Superego — a figura paterna como obstaculo a autoexpressao"),
    ("Sol","Jupiter","conjuncao","fusion",
     "Identidade expandida, otimismo e proposito grandioso",
     ["generosidade","sabedoria nata","fe em si mesmo","lideranca inspiradora"],
     "O Self em contato com o arquetipo do Rei Filosolo — expansao do ego para o universal.",
     "Principio do prazer ampliado — o ego encontra Eros expansivo"),
    ("Sol","Marte","conjuncao","fusion",
     "Identidade marcada por coragem e acao direta",
     ["coragem","iniciativa","lideranca","energia vital"],
     "O Heroi que age — ego e instinto guerreiro fundidos; determinacao como identidade.",
     "Id e Ego em fusao ativa — a pulsao de vida em expressao maxima"),
    ("Lua","Saturno","conjuncao","tension",
     "Mundo emocional contido pela estrutura",
     ["maturidade emocional","controle afetivo","amor responsavel","solidao interior"],
     "A Grande Mae encontra Saturno — a alma aprende que sentir tem consequencias (Jung). Repressao emocional estrutural (Freud).",
     "A Ancia e a Mae — emocao vivida atraves da restricao"),
    ("Lua","Saturno","oposicao","tension",
     "Tensao entre necessidades emocionais e restricoes externas",
     ["conflito nutricao-limite","mae e pai em guerra interna","maturidade forcada"],
     "A Lua (mae interna) em conflito com Saturno (pai interno) — o drama da crianca que precisou crescer cedo.",
     "Conflito Id/Superego no dominio afetivo"),
    ("Lua","Jupiter","conjuncao","flow",
     "Vida emocional rica, generosa e otimista",
     ["otimismo emocional","generosidade afetiva","fe no amor","abundancia"],
     "A alma ampliada — o mundo emocional vivido com expansao e fe. Grande capacidade de nutrir.",
     "Eros ampliado — o amor como abundancia e expansao"),
    ("Venus","Marte","conjuncao","fusion",
     "Fusao de amor e desejo",
     ["magnetismo sexual","criatividade passional","amor ativo","seducao natural"],
     "Anima e Animus em conjuncao — o masculino e o feminino internos integrados (Jung). Eros em plena forca (Freud).",
     "Hieros gamos: o casamento sagrado dos opostos internos"),
    ("Venus","Marte","oposicao","tension",
     "Tensao entre amor e desejo, dar e tomar",
     ["atração-repulsao","relacoes intensas e conflituosas","paixao que consome"],
     "Anima em tensao com Animus — o que amamos esta em guerra com o que desejamos (Jung). Conflito Eros/Tanatos (Freud).",
     "Os opostos que precisam do outro para existir — a tensao criativa do casal"),
    ("Venus","Saturno","conjuncao","tension",
     "Amor moldado pela responsabilidade e pelo tempo",
     ["amor duradouro","comprometimento serio","amor que constroi"],
     "A Deusa do amor mediada pelo Velho Sabio — o amor que so e real se resistir ao tempo.",
     "Eros mediado pelo principio de realidade — o prazer adiado como investimento"),
    ("Venus","Jupiter","conjuncao","flow",
     "Amor abundante, generoso e expansivo",
     ["generosidade afetiva","magnetismo social","prazer refinado","sorte no amor"],
     "Anima ampliada por Jupiter — o amor vivido com expansao, fe e generosidade.",
     "Eros em modo de expansao — prazer sem culpa e amor que transborda"),
    ("Mercurio","Urano","conjuncao","fusion",
     "Mente brilhante e revolucionaria",
     ["genialidade","insight subito","pensamento inovador","velocidade mental"],
     "O Trickster amplificado por Urano — mente como instrumento de ruptura e individuacao (Jung). Sublimacao intelectual de alta voltagem (Freud).",
     "Prometeu da mente — o pensamento que rouba fogo dos deuses"),
    ("Jupiter","Saturno","conjuncao","neutral",
     "Expansao contida pela disciplina",
     ["crescimento estruturado","sabedoria pratica","ambicao realista","autoridade ganha"],
     "O Sabio que aprendeu a expandir dentro de limites. Conjuncao que define geracoes inteiras.",
     "Principio de realidade canalizando o principio do prazer para conquistas duradouras"),
    ("Plutao","Sol","conjuncao","tension",
     "Poder transformador na identidade central",
     ["intensidade existencial","renascimento da identidade","poder pessoal imenso"],
     "A Sombra mais profunda tocando o Sol/ego — individuacao pela descida ao submundo (Jung). Tanatos na raiz da identidade (Freud).",
     "A Fenix como destino de vida — o ego que deve morrer e renascer"),
    ("Saturno","Nodo Norte","conjuncao","tension",
     "Missao evolutiva marcada por responsabilidade e maturidade",
     ["crescimento pela disciplina","karma de autoridade","maturidade como destino"],
     "Saturno no Nodo Norte indica uma alma chamada a construir estruturas e a assumir responsabilidade como caminho de crescimento.",
     "O superego como guia evolutivo — amadurecer e a propria transcendencia"),
    ("Quiron","Sol","conjuncao","tension",
     "A ferida que cura — a dor como proposito",
     ["cura dos outros","sabedoria pela dor","proposito terapeutico"],
     "Quiron (o Curador Ferido) toca o Sol — a identidade e moldada por uma ferida que, ao ser integrada, torna-se o maior dom (Jung).",
     "A ferida narcisica como fonte de empatia e cura — o analista que cura porque foi ferido"),
]


def _seed_aspects(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO aspect_meanings
           (planet_a, planet_b, aspect, nature, theme, keywords, psychological, jungian_note)
           VALUES (?,?,?,?,?,?,?,?)""",
        [
            (r[0], r[1], r[2], r[3], r[4],
             json.dumps(r[5], ensure_ascii=False),
             r[6], r[7])
            for r in _ASPECTS
        ],
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def run_seed() -> None:
    """Inicializa e popula o banco. Idempotente (INSERT OR IGNORE)."""
    init_db()
    conn = get_conn()
    try:
        print("[db] Inserindo casas...")
        _seed_houses(conn)
        print("[db] Inserindo planetas x signos...")
        _seed_planet_signs(conn)
        print("[db] Inserindo aspectos...")
        _seed_aspects(conn)
        conn.commit()
    finally:
        conn.close()

    # Relatório
    conn = get_conn()
    try:
        for table in ["house_meanings", "planet_sign_keywords", "aspect_meanings"]:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n} registros")
    finally:
        conn.close()
    print("[db] Seed concluido!")


if __name__ == "__main__":
    run_seed()

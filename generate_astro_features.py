"""Generate (or load) astrological features for the ML pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

import json
import logging
import math
import traceback

try:  # pragma: no cover - dependência opcional
    import pandas as pd
except ImportError:  # pragma: no cover - dependência opcional
    pd = None

try:  # pragma: no cover - dependências opcionais
    from immanuel import charts
    import swisseph as swe  # type: ignore
except ImportError:  # pragma: no cover - dependências opcionais
    charts = None  # type: ignore
    swe = None  # type: ignore


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = BASE_DIR / "pantheon_reduced_1000.csv"
SAMPLE_INPUT_FILE = DATA_DIR / "sample_pantheon_reduced_1000.csv"
OUTPUT_FILE = BASE_DIR / "astrological_features.csv"
SAMPLE_OUTPUT_FILE = DATA_DIR / "sample_astrological_features.csv"

SIGN_RULERS_TRADITIONAL = {
    "aries": "Mars",
    "taurus": "Venus",
    "gemini": "Mercury",
    "cancer": "Moon",
    "leo": "Sun",
    "virgo": "Mercury",
    "libra": "Venus",
    "scorpio": "Mars",
    "sagittarius": "Jupiter",
    "capricorn": "Saturn",
    "aquarius": "Saturn",
    "pisces": "Jupiter",
}

SIGN_RULERS_MODERN = {
    "aries": "Mars",
    "taurus": "Venus",
    "gemini": "Mercury",
    "cancer": "Moon",
    "leo": "Sun",
    "virgo": "Mercury",
    "libra": "Venus",
    "scorpio": "Pluto",
    "sagittarius": "Jupiter",
    "capricorn": "Saturn",
    "aquarius": "Uranus",
    "pisces": "Neptune",
}


TEMPERAMENT_BY_ELEMENT = {
    "fire": "Choleric",
    "air": "Sanguine",
    "earth": "Melancholic",
    "water": "Phlegmatic",
}


PLANETARY_TEMPERAMENTS = {
    "sun": "Choleric",
    "moon": "Phlegmatic",
    "mercury": "Sanguine",
    "venus": "Sanguine",
    "mars": "Choleric",
    "jupiter": "Sanguine",
    "saturn": "Melancholic",
    "uranus": "Choleric",
    "neptune": "Phlegmatic",
    "pluto": "Melancholic",
}


TEMPERAMENT_PROFILES = {
    "Choleric": {
        "professions": [
            "Executivo visionário",
            "Empreendedor",
            "Líder militar",
        ],
        "challenges": "Canalizar impulsividade, evitar autoritarismo e excesso de controle.",
    },
    "Sanguine": {
        "professions": [
            "Comunicador",
            "Artista performático",
            "Educador inspirador",
        ],
        "challenges": "Manter foco, estruturar ideias e concretizar projetos de longo prazo.",
    },
    "Melancholic": {
        "professions": [
            "Pesquisador",
            "Artesão de precisão",
            "Estrategista",
        ],
        "challenges": "Evitar excesso de crítica, perfeccionismo paralisante e isolamento.",
    },
    "Phlegmatic": {
        "professions": [
            "Mentor cuidador",
            "Terapeuta holístico",
            "Diplomata",
        ],
        "challenges": "Lidar com acomodação, dificuldade em dizer não e dispersão emocional.",
    },
}


ELEMENT_SEQUENCE = ["fire", "earth", "air", "water"]


def _normalize_degree(value: float | int | None) -> float | None:
    if value is None:
        return None
    normalized = math.fmod(float(value), 360.0)
    if normalized < 0:
        normalized += 360.0
    return round(normalized, 1)


def _resolve_degree(obj) -> float | None:
    for attr in ("longitude", "lon", "lambda_", "position"):
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if isinstance(value, (int, float)):
                return _normalize_degree(value)
            if attr == "position" and hasattr(value, "longitude"):
                pos_val = getattr(value, "longitude")
                if isinstance(pos_val, (int, float)):
                    return _normalize_degree(pos_val)
    return None


def _resolve_dispositors(sign_name: str | None) -> tuple[str | None, str | None]:
    if not sign_name:
        return None, None
    key = sign_name.lower()
    trad = SIGN_RULERS_TRADITIONAL.get(key)
    modern = SIGN_RULERS_MODERN.get(key, trad)
    return trad, modern


def _resolve_temperament_from_element(element: str | None) -> str | None:
    if not element:
        return None
    return TEMPERAMENT_BY_ELEMENT.get(element.lower())


def _resolve_temperament_from_body(body: str | None) -> str | None:
    if not body:
        return None
    return PLANETARY_TEMPERAMENTS.get(body.lower())


def _resolve_dispositor_element(body: str | None, found_objects: dict[str, object]) -> str | None:
    if not body:
        return None
    body_key = body.lower()
    obj = found_objects.get(body_key)
    if not obj:
        return None
    if hasattr(obj, "sign") and getattr(obj, "sign") and hasattr(obj.sign, "element"):
        return obj.sign.element
    return None


def get_astrological_data(row):
    features = {
        'name': row['name'],
        'occupation': row['occupation'],
    }
    try:
        birth_date_str = row['birthdate']
        birth_datetime_str = f"{birth_date_str} 12:00:00"
        birth_datetime = datetime.strptime(birth_datetime_str, '%Y-%m-%d %H:%M:%S')
        
        latitude = row['bplace_lat']
        longitude = row['bplace_lon']

        native = charts.Subject(
            date_time=birth_datetime,
            latitude=latitude,
            longitude=longitude,
        )

        natal = charts.Natal(native)
        # logging.debug(f"Natal chart created for {row['name']}. Objects keys: {natal.objects.keys()}")

        celestial_objects = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

        temperament_counts = {name: 0 for name in TEMPERAMENT_PROFILES.keys()}
        trad_dispositor_counts = {name: 0 for name in TEMPERAMENT_PROFILES.keys()}
        modern_dispositor_counts = {name: 0 for name in TEMPERAMENT_PROFILES.keys()}
        trad_dispositor_element_counts = {element: 0 for element in ELEMENT_SEQUENCE}
        modern_dispositor_element_counts = {element: 0 for element in ELEMENT_SEQUENCE}
        found_objects: dict[str, object | None] = {}

        for obj_name_expected in celestial_objects:
            obj_prefix = obj_name_expected.lower()
            found_obj = None
            # Acessar objetos celestes diretamente pelo nome, se disponível como atributo do objeto natal
            # A documentação sugere que os objetos celestes são acessíveis como atributos do objeto natal
            # ou através de natal.objects, onde as chaves são IDs numéricos e os objetos têm um atributo 'name'.
            # Vamos tentar acessar via getattr primeiro, que é mais direto se o objeto estiver lá.
            found_obj = getattr(natal, obj_name_expected.lower(), None)
            
            # Se não encontrado como atributo direto, tentar procurar em natal.objects
            if not found_obj:
                for obj_id, obj_data in natal.objects.items():
                    if hasattr(obj_data, 'name') and obj_data.name == obj_name_expected:
                        found_obj = obj_data
                        break
            
            if found_obj:
                found_objects[obj_prefix] = found_obj
                sign_value = found_obj.sign.name if hasattr(found_obj, 'sign') and found_obj.sign else None
                features[f'{obj_prefix}_sign'] = sign_value
                features[f'{obj_prefix}_house'] = found_obj.house.number if hasattr(found_obj, 'house') and found_obj.house else None
                features[f'{obj_prefix}_element'] = found_obj.sign.element if hasattr(found_obj, 'sign') and found_obj.sign and hasattr(found_obj.sign, 'element') else None
                features[f'{obj_prefix}_modality'] = found_obj.sign.modality if hasattr(found_obj, 'sign') and found_obj.sign and hasattr(found_obj.sign, 'modality') else None
                features[f'{obj_prefix}_aspects'] = json.dumps([str(a) for a in found_obj.aspects]) if hasattr(found_obj, 'aspects') and found_obj.aspects else None
                features[f'{obj_prefix}_degree'] = _resolve_degree(found_obj)
                trad_ruler, modern_ruler = _resolve_dispositors(sign_value)
                features[f'{obj_prefix}_dispositor_traditional'] = trad_ruler
                features[f'{obj_prefix}_dispositor_modern'] = modern_ruler
                temperament = _resolve_temperament_from_element(features[f'{obj_prefix}_element'])
                features[f'{obj_prefix}_temperament'] = temperament
                if temperament:
                    temperament_counts[temperament] += 1
                trad_temperament = _resolve_temperament_from_body(trad_ruler)
                modern_temperament = _resolve_temperament_from_body(modern_ruler)
                features[f'{obj_prefix}_dispositor_traditional_temperament'] = trad_temperament
                features[f'{obj_prefix}_dispositor_modern_temperament'] = modern_temperament
                if trad_temperament:
                    trad_dispositor_counts[trad_temperament] += 1
                if modern_temperament:
                    modern_dispositor_counts[modern_temperament] += 1
                # logging.debug(f"  Extracted {obj_name_expected}: Sign={features[f'{obj_prefix}_sign']}, House={features[f'{obj_prefix}_house']}")
            else:
                found_objects[obj_prefix] = None
                features[f'{obj_prefix}_sign'] = None
                features[f'{obj_prefix}_house'] = None
                features[f'{obj_prefix}_element'] = None
                features[f'{obj_prefix}_modality'] = None
                features[f'{obj_prefix}_aspects'] = None
                features[f'{obj_prefix}_degree'] = None
                features[f'{obj_prefix}_dispositor_traditional'] = None
                features[f'{obj_prefix}_dispositor_modern'] = None
                features[f'{obj_prefix}_temperament'] = None
                features[f'{obj_prefix}_dispositor_traditional_temperament'] = None
                features[f'{obj_prefix}_dispositor_modern_temperament'] = None
                # logging.debug(f"  {obj_name_expected} not found.")

        for obj_name_expected in celestial_objects:
            obj_prefix = obj_name_expected.lower()
            trad_dispositor = features.get(f'{obj_prefix}_dispositor_traditional')
            modern_dispositor = features.get(f'{obj_prefix}_dispositor_modern')

            trad_element = _resolve_dispositor_element(trad_dispositor, found_objects)
            modern_element = _resolve_dispositor_element(modern_dispositor, found_objects)

            features[f'{obj_prefix}_dispositor_traditional_element'] = trad_element
            features[f'{obj_prefix}_dispositor_modern_element'] = modern_element

            trad_element_key = trad_element.lower() if isinstance(trad_element, str) else None
            modern_element_key = modern_element.lower() if isinstance(modern_element, str) else None

            if trad_element_key in trad_dispositor_element_counts:
                trad_dispositor_element_counts[trad_element_key] += 1
            if modern_element_key in modern_dispositor_element_counts:
                modern_dispositor_element_counts[modern_element_key] += 1

        for temperament_name in TEMPERAMENT_PROFILES.keys():
            features[f'temperament_{temperament_name.lower()}_count'] = temperament_counts[temperament_name]
            features[f'temperament_traditional_dispositor_{temperament_name.lower()}_count'] = trad_dispositor_counts[temperament_name]
            features[f'temperament_modern_dispositor_{temperament_name.lower()}_count'] = modern_dispositor_counts[temperament_name]

        for element in ELEMENT_SEQUENCE:
            features[f'element_traditional_dispositor_{element}_count'] = trad_dispositor_element_counts[element]
            features[f'element_modern_dispositor_{element}_count'] = modern_dispositor_element_counts[element]

        dominant_trad_element = max(
            trad_dispositor_element_counts.items(),
            key=lambda item: item[1],
        ) if trad_dispositor_element_counts else None

        dominant_modern_element = max(
            modern_dispositor_element_counts.items(),
            key=lambda item: item[1],
        ) if modern_dispositor_element_counts else None

        features['element_traditional_dispositor_dominant'] = (
            dominant_trad_element[0]
            if dominant_trad_element and dominant_trad_element[1] > 0
            else None
        )
        features['element_modern_dispositor_dominant'] = (
            dominant_modern_element[0]
            if dominant_modern_element and dominant_modern_element[1] > 0
            else None
        )

        dominant_temperament = None
        if temperament_counts:
            dominant_temperament = max(
                temperament_counts.items(),
                key=lambda item: item[1],
            )
            dominant_temperament = dominant_temperament[0] if dominant_temperament[1] > 0 else None

        if dominant_temperament:
            profile = TEMPERAMENT_PROFILES[dominant_temperament]
            features['temperament_profile_primary'] = dominant_temperament
            features['temperament_profile_primary_professions'] = "; ".join(profile['professions'])
            features['temperament_profile_primary_challenges'] = profile['challenges']
        else:
            features['temperament_profile_primary'] = None
            features['temperament_profile_primary_professions'] = None
            features['temperament_profile_primary_challenges'] = None

        # Tratar Ascendente e Meio do Céu de forma mais robusta
        ascendant_obj = getattr(natal, 'ascendant', None)
        if ascendant_obj:
            features['ascendant_sign'] = ascendant_obj.sign.name if hasattr(ascendant_obj, 'sign') and ascendant_obj.sign else None
            features['ascendant_house'] = ascendant_obj.house.number if hasattr(ascendant_obj, 'house') and ascendant_obj.house else None
            # logging.debug(f"  Ascendant: Sign={features['ascendant_sign']}, House={features['ascendant_house']}")
        else:
            features['ascendant_sign'] = None
            features['ascendant_house'] = None
            # logging.debug("  Ascendant not found or is None.")

        mc_obj = getattr(natal, 'mc', None)
        if mc_obj:
            features['mc_sign'] = mc_obj.sign.name if hasattr(mc_obj, 'sign') and mc_obj.sign else None
            features['mc_house'] = mc_obj.house.number if hasattr(mc_obj, 'house') and mc_obj.house else None
            # logging.debug(f"  MC: Sign={features['mc_sign']}, House={features['mc_house']}")
        else:
            features['mc_sign'] = None
            features['mc_house'] = None
            # logging.debug("  MC not found or is None.")

        return features
    except swe.Error as se:  # type: ignore[attr-defined]
        logging.warning(f"Erro swisseph ao processar {row['name']}: {se}. Ignorando este registro.")
        return None
    except Exception as e:
        logging.error(f"Erro inesperado ao processar {row['name']}: {e}")
        logging.error(traceback.format_exc())
        return None

def _copy_sample_output() -> None:
    logging.info("Carregando características astrológicas de amostra em %s", OUTPUT_FILE)
    if pd is not None:
        sample_df = pd.read_csv(SAMPLE_OUTPUT_FILE)
        sample_df.to_csv(OUTPUT_FILE, index=False)
    else:
        shutil.copyfile(SAMPLE_OUTPUT_FILE, OUTPUT_FILE)


def main() -> None:
    if charts is None or swe is None or pd is None:
        logging.warning(
            "Dependências opcionais ausentes. Utilizando dados de amostra."
        )
        _copy_sample_output()
        return

    source_file = INPUT_FILE if INPUT_FILE.exists() else SAMPLE_INPUT_FILE
    if source_file == SAMPLE_INPUT_FILE:
        logging.warning(
            "Arquivo %s não encontrado. Utilizando entrada de amostra %s.", INPUT_FILE.name, source_file
        )
    else:
        logging.info("Carregando dados reduzidos de %s", source_file)

    df_reduced = pd.read_csv(source_file)

    astro_data_list = []
    for _, row in df_reduced.iterrows():
        data = get_astrological_data(row)
        if data:
            astro_data_list.append(data)

    if astro_data_list:
        astro_features_df = pd.DataFrame(astro_data_list)
        astro_features_df.to_csv(OUTPUT_FILE, index=False)
        logging.info("Características astrológicas geradas e salvas em %s", OUTPUT_FILE)
    else:
        logging.warning("Nenhuma característica astrológica foi gerada; carregando dados de amostra.")
        _copy_sample_output()


if __name__ == "__main__":
    main()


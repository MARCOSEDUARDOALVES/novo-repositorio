"""Generate (or load) astrological features for the ML pipeline."""

from datetime import datetime
from pathlib import Path
import shutil

import json
import logging
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
                features[f'{obj_prefix}_sign'] = found_obj.sign.name if hasattr(found_obj, 'sign') and found_obj.sign else None
                features[f'{obj_prefix}_house'] = found_obj.house.number if hasattr(found_obj, 'house') and found_obj.house else None
                features[f'{obj_prefix}_element'] = found_obj.sign.element if hasattr(found_obj, 'sign') and found_obj.sign and hasattr(found_obj.sign, 'element') else None
                features[f'{obj_prefix}_modality'] = found_obj.sign.modality if hasattr(found_obj, 'sign') and found_obj.sign and hasattr(found_obj.sign, 'modality') else None
                features[f'{obj_prefix}_aspects'] = json.dumps([str(a) for a in found_obj.aspects]) if hasattr(found_obj, 'aspects') and found_obj.aspects else None
                # logging.debug(f"  Extracted {obj_name_expected}: Sign={features[f'{obj_prefix}_sign']}, House={features[f'{obj_prefix}_house']}")
            else:
                features[f'{obj_prefix}_sign'] = None
                features[f'{obj_prefix}_house'] = None
                features[f'{obj_prefix}_element'] = None
                features[f'{obj_prefix}_modality'] = None
                features[f'{obj_prefix}_aspects'] = None
                # logging.debug(f"  {obj_name_expected} not found.")

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


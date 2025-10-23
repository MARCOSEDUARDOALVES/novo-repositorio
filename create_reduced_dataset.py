"""Create a reduced Pantheon dataset that feeds the feature generator."""

from pathlib import Path
import shutil

import logging

from astro_database_client import AstroDatabaseClient, AstroDatabaseError

try:  # pragma: no cover - dependência opcional
    import pandas as pd
except ImportError:  # pragma: no cover - dependência opcional
    pd = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "pantheon_cleaned_data.csv"
SAMPLE_FILE = BASE_DIR / "data" / "sample_pantheon_cleaned_data.csv"
OUTPUT_FILE = BASE_DIR / "pantheon_reduced_1000.csv"

MAX_RECORDS = 1000


def main() -> None:
    if pd is None:
        logging.warning(
            "Pandas não está disponível. Copiando subconjunto de amostra para %s.", OUTPUT_FILE
        )
        shutil.copyfile(SAMPLE_FILE, OUTPUT_FILE)
        return

    if INPUT_FILE.exists():
        logging.info("Carregando dados limpos de %s", INPUT_FILE)
        df = pd.read_csv(INPUT_FILE)
    else:
        try:
            client = AstroDatabaseClient()
            records = client.fetch_cleaned_people(limit=MAX_RECORDS)
            if not records:
                raise AstroDatabaseError("O banco astrológico não retornou registros limpos.")
            df = pd.DataFrame(records)
            logging.info(
                "Dados limpos carregados diretamente do banco astrológico (%s registros).",
                len(df),
            )
        except AstroDatabaseError as exc:
            logging.warning(
                "Não foi possível obter dados limpos do banco astrológico: %s", exc
            )
            logging.warning(
                "Arquivo %s não encontrado. Utilizando amostra em %s.", INPUT_FILE.name, SAMPLE_FILE
            )
            df = pd.read_csv(SAMPLE_FILE)

    df_reduced = df.head(MAX_RECORDS)
    df_reduced.to_csv(OUTPUT_FILE, index=False)
    logging.info(
        "Subconjunto com até %s registros salvo em %s", MAX_RECORDS, OUTPUT_FILE
    )


if __name__ == "__main__":
    main()

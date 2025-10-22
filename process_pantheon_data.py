"""Helper utilities for cleaning the Pantheon dataset used in the ML pipeline.

This module now ships with a tiny, self-contained sample dataset so the data
preparation steps can be executed locally without external downloads. When the
real ``person_2025_update.csv`` file is missing we transparently fall back to
the bundled sample allowing the rest of the pipeline to run out-of-the-box.
"""

from pathlib import Path
import shutil
from typing import TYPE_CHECKING

import logging

try:  # pragma: no cover - dependência opcional
    import pandas as pd
except ImportError:  # pragma: no cover - dependência opcional
    pd = None

if TYPE_CHECKING:  # pragma: no cover - type hints
    from pandas import DataFrame


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SOURCE_FILE = BASE_DIR / "person_2025_update.csv"
SAMPLE_FILE = DATA_DIR / "sample_person_2025_update.csv"
OUTPUT_FILE = BASE_DIR / "pantheon_cleaned_data.csv"

REQUIRED_COLUMNS = [
    "name",
    "occupation",
    "birthdate",
    "bplace_name",
    "bplace_lat",
    "bplace_lon",
]


def load_source_dataframe() -> "DataFrame":
    """Return the raw Pantheon dataframe or the bundled sample fallback."""

    if SOURCE_FILE.exists():
        logging.info("Carregando dados a partir de %s", SOURCE_FILE)
        return pd.read_csv(SOURCE_FILE)

    logging.warning(
        "Arquivo %s não encontrado. Utilizando amostra em %s.", SOURCE_FILE.name, SAMPLE_FILE
    )
    return pd.read_csv(SAMPLE_FILE)


def clean_dataset(df: "DataFrame") -> "DataFrame":
    """Filter and clean the Pantheon dataframe to the columns used downstream."""

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing_cols}")

    df_filtered = df[REQUIRED_COLUMNS].copy()
    df_filtered.dropna(inplace=True)

    logging.info(
        "Após remover valores nulos nas colunas obrigatórias: %s", df_filtered.shape
    )

    df_filtered["birth_date_parsed"] = pd.to_datetime(df_filtered["birthdate"], errors="coerce")
    df_filtered.dropna(subset=["birth_date_parsed"], inplace=True)

    logging.info(
        "Após converter datas de nascimento válidas: %s", df_filtered.shape
    )

    return df_filtered


def main() -> None:
    if pd is None:
        logging.warning(
            "Pandas não está disponível. Copiando dados limpos de amostra para %s.", OUTPUT_FILE
        )
        shutil.copyfile(SAMPLE_FILE, OUTPUT_FILE)
        return

    df = load_source_dataframe()
    logging.info("Dataset original: %s linhas, %s colunas", *df.shape)

    df_filtered = clean_dataset(df)

    logging.info("Exemplo de registros limpos:\n%s", df_filtered.head())

    df_filtered.to_csv(OUTPUT_FILE, index=False)
    logging.info("Dados limpos salvos em %s", OUTPUT_FILE)


if __name__ == "__main__":
    main()

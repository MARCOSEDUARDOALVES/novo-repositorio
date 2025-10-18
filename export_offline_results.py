"""Utility to package offline pipeline outputs for distribution."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
import shutil
import zipfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "offline_results"

OUTPUT_SPEC = [
    {
        "source": BASE_DIR / "pantheon_cleaned_data.csv",
        "target": "pantheon_cleaned_data.csv",
        "description": "Dados Pantheon limpos (pré-processados).",
    },
    {
        "source": BASE_DIR / "pantheon_reduced_1000.csv",
        "target": "pantheon_reduced_1000.csv",
        "description": "Subconjunto reduzido do Pantheon para experimentos locais.",
    },
    {
        "source": BASE_DIR / "astrological_features.csv",
        "target": "astrological_features.csv",
        "description": "Características astrológicas derivadas usadas no ML.",
    },
    {
        "source": BASE_DIR / "prepared_ml_data.csv",
        "target": "prepared_ml_data.csv",
        "description": "Dados vetorizados prontos para treinamento e avaliação.",
    },
    {
        "source": BASE_DIR / "occupation_label_mapping.json",
        "target": "occupation_label_mapping.json",
        "description": "Mapeamento numérico das ocupações do conjunto preparado.",
    },
    {
        "source": BASE_DIR / "random_forest_model.pkl",
        "target": "random_forest_model.pkl",
        "description": "Modelo RandomForest offline (gerado localmente, se disponível).",
    },
    {
        "source": DATA_DIR / "sample_model_report.txt",
        "target": "model_report.txt",
        "description": "Relatório de classificação associado ao modelo offline.",
    },
    {
        "source": DATA_DIR / "sample_model_metrics.json",
        "target": "model_metrics.json",
        "description": "Resumo textual das métricas do modelo de amostra.",
    },
]


def export_offline_bundle() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    exported_files = []
    for entry in OUTPUT_SPEC:
        source: Path = entry["source"]
        destination = OUTPUT_DIR / entry["target"]
        description = entry["description"]

        if not source.exists():
            logging.warning("Arquivo %s não encontrado; ignorando.", source)
            continue

        shutil.copy2(source, destination)
        logging.info("Arquivo copiado para %s", destination)
        exported_files.append(
            {
                "filename": entry["target"],
                "description": description,
                "source": str(source.relative_to(BASE_DIR)),
                "output_path": str(destination.relative_to(BASE_DIR)),
            }
        )

    timestamp = datetime.utcnow().isoformat() + "Z"
    manifest = {
        "generated_at": timestamp,
        "files": exported_files,
    }

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    manifest_path.write_text(manifest_content, encoding="utf-8")
    logging.info("Manifesto salvo em %s", manifest_path)

    readme_path = OUTPUT_DIR / "README.md"
    readme_lines = [
        "# Pacote de resultados offline",
        "",
        "Este diretório contém os artefatos gerados pelo pipeline offline.",
        "O arquivo `manifest.json` lista cada item e sua origem no repositório.",
        "",
        "## Conteúdo incluso",
    ]

    for item in exported_files:
        readme_lines.append(f"- `{item['filename']}` — {item['description']}")

    readme_lines.extend(
        [
        "",
        "Para obter um arquivo ZIP pronto para envio, execute:",
        "",
        "```bash",
        "python export_offline_results.py --zip",
        "```",
        "",
        "O arquivo `.zip` não é versionado para evitar anexos binários incompatíveis; gere-o localmente conforme necessário.",
    ])
    readme_content = "\n".join(readme_lines) + "\n"
    readme_path.write_text(readme_content, encoding="utf-8")

    logging.info("README gerado em %s", readme_path)


def build_zip_archive() -> Path | None:
    exported_files = [f for f in OUTPUT_SPEC if (OUTPUT_DIR / f["target"]).exists()]
    if not exported_files:
        logging.warning("Nenhum arquivo exportado para compactar.")
        return None

    zip_path = OUTPUT_DIR / "offline_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for entry in exported_files:
            filename = entry["target"]
            file_path = OUTPUT_DIR / filename
            zip_file.write(file_path, arcname=filename)
        manifest_path = OUTPUT_DIR / "manifest.json"
        if manifest_path.exists():
            zip_file.write(manifest_path, arcname="manifest.json")
    logging.info("Arquivo ZIP criado em %s", zip_path)
    return zip_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Empacota os artefatos do pipeline offline.")
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Também gera um arquivo offline_bundle.zip com os artefatos exportados.",
    )
    args = parser.parse_args()

    export_offline_bundle()
    if args.zip:
        build_zip_archive()


if __name__ == "__main__":
    main()

# Pacote de resultados offline

Este diretório contém os artefatos gerados pelo pipeline offline.
O arquivo `manifest.json` lista cada item e sua origem no repositório.

## Conteúdo incluso
- `pantheon_cleaned_data.csv` — Dados Pantheon limpos (pré-processados).
- `pantheon_reduced_1000.csv` — Subconjunto reduzido do Pantheon para experimentos locais.
- `astrological_features.csv` — Características astrológicas derivadas usadas no ML.
- `prepared_ml_data.csv` — Dados vetorizados prontos para treinamento e avaliação.
- `occupation_label_mapping.json` — Mapeamento numérico das ocupações do conjunto preparado.
- `model_report.txt` — Relatório de classificação associado ao modelo offline.
- `model_metrics.json` — Resumo textual das métricas do modelo de amostra.

Para obter um arquivo ZIP pronto para envio, execute:

```bash
python export_offline_results.py --zip
```

O arquivo `.zip` não é versionado para evitar anexos binários incompatíveis; gere-o localmente conforme necessário.

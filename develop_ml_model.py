import json
import logging
import traceback
from pathlib import Path
import pickle

from astro_database_client import AstroDatabaseClient, AstroDatabaseError

try:  # pragma: no cover - dependências opcionais
    import joblib
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
except ImportError:  # pragma: no cover - dependências opcionais
    joblib = None
    pd = None
    RandomForestClassifier = None
    accuracy_score = None
    classification_report = None
    train_test_split = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = BASE_DIR / "prepared_ml_data.csv"
SAMPLE_INPUT_FILE = DATA_DIR / "sample_prepared_ml_data.csv"
OCCUPATION_MAPPING_FILE = BASE_DIR / "occupation_label_mapping.json"
SAMPLE_MAPPING_FILE = DATA_DIR / "sample_occupation_label_mapping.json"
MODEL_OUTPUT_FILE = BASE_DIR / "random_forest_model.pkl"
SAMPLE_MODEL_REPORT = DATA_DIR / "sample_model_report.txt"
SAMPLE_MODEL_METRICS = DATA_DIR / "sample_model_metrics.json"


def _load_prepared_dataframe():
    if pd is None:
        raise RuntimeError("Pandas é obrigatório para carregar os dados preparados.")

    if INPUT_FILE.exists():
        logging.info("Dados preparados carregados do arquivo: %s", INPUT_FILE)
        return pd.read_csv(INPUT_FILE)

    try:
        client = AstroDatabaseClient()
        records = client.fetch_prepared_ml_dataset()
        if not records:
            raise AstroDatabaseError("O banco astrológico não retornou dados preparados.")
        df_remote = pd.DataFrame(records)
        logging.info(
            "Dados preparados carregados diretamente do banco astrológico (%s registros).",
            len(df_remote),
        )
        return df_remote
    except AstroDatabaseError as exc:
        logging.warning("Falha ao consultar o banco astrológico: %s", exc)

    logging.warning(
        "Arquivo %s não encontrado. Utilizando dados preparados de amostra %s.",
        INPUT_FILE.name,
        SAMPLE_INPUT_FILE,
    )
    return pd.read_csv(SAMPLE_INPUT_FILE)


def develop_model():
    if None in (pd, RandomForestClassifier, accuracy_score, classification_report, train_test_split, joblib):
        logging.warning(
            "Dependências de machine learning ausentes. Gerando modelo fictício com métricas de amostra."
        )

        accuracy = None
        if SAMPLE_MODEL_METRICS.exists():
            try:
                metrics_data = json.loads(SAMPLE_MODEL_METRICS.read_text(encoding="utf-8"))
                accuracy = metrics_data.get("accuracy")
            except json.JSONDecodeError as exc:  # pragma: no cover - cenário improvável
                logging.error("Falha ao ler métricas de amostra: %s", exc)

        placeholder_model = {
            "model_type": "offline_placeholder",
            "generated_from": "sample_dataset",
            "accuracy": accuracy,
            "notes": "Modelo indisponível porque dependências de ML não estão instaladas.",
        }

        try:
            with MODEL_OUTPUT_FILE.open("wb") as model_fp:
                pickle.dump(placeholder_model, model_fp)
            logging.info("Modelo fictício salvo em %s", MODEL_OUTPUT_FILE)
        except OSError as exc:  # pragma: no cover - falha de I/O inesperada
            logging.error("Não foi possível salvar o modelo fictício: %s", exc)

        report = SAMPLE_MODEL_REPORT.read_text(encoding="utf-8") if SAMPLE_MODEL_REPORT.exists() else None

        return placeholder_model, accuracy, report

    try:
        df_prepared = _load_prepared_dataframe()
        logging.info(f"Dimensões dos dados preparados: {df_prepared.shape}")

        # Separar features (X) e target (y)
        X = df_prepared.drop(columns=['name', 'occupation', 'occupation_encoded'])
        y = df_prepared['occupation_encoded']

        # Identificar classes com apenas um membro para evitar erro no train_test_split com stratify
        class_counts = y.value_counts()
        rare_classes = class_counts[class_counts < 2].index

        # Remover amostras de classes raras do conjunto de dados
        df_filtered = df_prepared[~y.isin(rare_classes)]
        X_filtered = df_filtered.drop(columns=['name', 'occupation', 'occupation_encoded'])
        y_filtered = df_filtered['occupation_encoded']
        
        logging.info(f"Classes raras removidas. Novas dimensões: {df_filtered.shape}")

        # Dividir os dados em conjuntos de treinamento e teste
        X_train, X_test, y_train, y_test = train_test_split(X_filtered, y_filtered, test_size=0.2, random_state=42, stratify=y_filtered)
        logging.info(f"Dados divididos: Treino={X_train.shape}, Teste={X_test.shape}")

        # Inicializar e treinar o modelo RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        logging.info("Iniciando treinamento do modelo RandomForestClassifier...")
        model.fit(X_train, y_train)
        logging.info("Treinamento do modelo concluído.")

        # Salvar o modelo treinado
        joblib.dump(model, MODEL_OUTPUT_FILE)
        logging.info(f"Modelo salvo em {MODEL_OUTPUT_FILE}")

        # Fazer previsões no conjunto de teste
        y_pred = model.predict(X_test)

        # Avaliar o modelo
        accuracy = accuracy_score(y_test, y_pred)
        logging.info(f"Acurácia do modelo: {accuracy:.4f}")

        # Carregar o mapeamento de profissões completo
        mapping_file = (
            OCCUPATION_MAPPING_FILE if OCCUPATION_MAPPING_FILE.exists() else SAMPLE_MAPPING_FILE
        )
        with open(mapping_file, 'r') as f:
            full_occupation_labels = json.load(f)
        
        # Obter as classes presentes no conjunto de teste e suas respectivas labels
        unique_test_labels = sorted(y_test.unique())
        target_names_for_report = [full_occupation_labels[i] for i in unique_test_labels]

        # Gerar relatório de classificação
        report = classification_report(y_test, y_pred, labels=unique_test_labels, target_names=target_names_for_report, zero_division=0)
        logging.info("Relatório de Classificação:\n" + report)

        return model, accuracy, report

    except FileNotFoundError:
        logging.error(
            "Erro: O arquivo %s ou %s não foi encontrado.", INPUT_FILE, OCCUPATION_MAPPING_FILE
        )
        return None, None, None
    except Exception as e:
        logging.error(f"Ocorreu um erro durante o desenvolvimento do modelo: {e}")
        logging.error(traceback.format_exc())
        return None, None, None

if __name__ == '__main__':
    develop_model()

import json
import logging
import traceback
from pathlib import Path
import shutil

from astro_database_client import AstroDatabaseClient, AstroDatabaseError

try:  # pragma: no cover - dependências opcionais
    import pandas as pd
    from sklearn.preprocessing import OneHotEncoder, LabelEncoder
except ImportError:  # pragma: no cover - dependências opcionais
    pd = None
    OneHotEncoder = None
    LabelEncoder = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = BASE_DIR / "astrological_features.csv"
SAMPLE_INPUT_FILE = DATA_DIR / "sample_astrological_features.csv"
OUTPUT_FILE = BASE_DIR / "prepared_ml_data.csv"
SAMPLE_OUTPUT_FILE = DATA_DIR / "sample_prepared_ml_data.csv"
OCCUPATION_MAPPING_FILE = BASE_DIR / "occupation_label_mapping.json"
SAMPLE_MAPPING_FILE = DATA_DIR / "sample_occupation_label_mapping.json"


def _load_feature_dataframe():
    if pd is None:
        raise RuntimeError("Pandas é obrigatório para carregar as características astrológicas.")

    if INPUT_FILE.exists():
        logging.info("Dados carregados do arquivo: %s", INPUT_FILE)
        return pd.read_csv(INPUT_FILE)

    try:
        client = AstroDatabaseClient()
        records = client.fetch_astrological_features()
        if not records:
            raise AstroDatabaseError("O banco astrológico não retornou características.")
        df_remote = pd.DataFrame(records)
        logging.info(
            "Características carregadas diretamente do banco astrológico (%s registros).",
            len(df_remote),
        )
        return df_remote
    except AstroDatabaseError as exc:
        logging.warning("Falha ao consultar o banco astrológico: %s", exc)

    logging.warning(
        "Arquivo %s não encontrado. Utilizando dados de amostra %s.",
        INPUT_FILE.name,
        SAMPLE_INPUT_FILE,
    )
    return pd.read_csv(SAMPLE_INPUT_FILE)


def prepare_data(df):
    if OneHotEncoder is None:
        raise RuntimeError("scikit-learn não está disponível para preparar os dados")

    # Preencher valores ausentes para colunas categóricas com 'Unknown'
    categorical_cols = [
        col
        for col in df.columns
        if (
            not col.endswith('_count')
            and (
                'sign' in col
                or 'element' in col
                or 'modality' in col
                or 'dispositor' in col
                or 'temperament' in col
            )
        )
    ]
    for col in categorical_cols:
        df[col] = df[col].fillna('Unknown')

    # Preencher valores ausentes para colunas numéricas (casas) com 0 ou -1 (indicando desconhecido)
    numeric_cols = [
        col
        for col in df.columns
        if 'house' in col or 'degree' in col or col.endswith('_count')
    ]
    for col in numeric_cols:
        fill_value = -1 if col.endswith('_degree') else 0
        df[col] = df[col].fillna(fill_value)

    # Processar a coluna de aspectos
    # Para simplificar, vamos extrair o número de aspectos para cada objeto celeste
    # Uma abordagem mais complexa envolveria one-hot encoding para cada tipo de aspecto
    aspect_cols = [col for col in df.columns if '_aspects' in col]
    for col in aspect_cols:
        df[col] = df[col].apply(lambda x: len(json.loads(x)) if pd.notna(x) and x != 'None' else 0)

    # Codificação One-Hot para variáveis categóricas
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    encoded_features = encoder.fit_transform(df[categorical_cols])
    encoded_feature_names = encoder.get_feature_names_out(categorical_cols)
    encoded_df = pd.DataFrame(encoded_features, columns=encoded_feature_names, index=df.index)

    # Remover colunas categóricas originais e adicionar as codificadas
    df = df.drop(columns=categorical_cols)
    df = pd.concat([df, encoded_df], axis=1)

    # Remover colunas de aspectos originais, já que foram processadas
    # Apenas remover se ainda existirem e não forem parte das colunas codificadas (o que não deveriam ser)
    df = df.drop(columns=[col for col in aspect_cols if col in df.columns])

    return df

def main() -> None:
    if pd is None or OneHotEncoder is None or LabelEncoder is None:
        logging.warning(
            "Dependências de ciência de dados ausentes. Copiando dados preparados de amostra para %s.",
            OUTPUT_FILE,
        )
        if SAMPLE_OUTPUT_FILE.exists() and SAMPLE_MAPPING_FILE.exists():
            shutil.copyfile(SAMPLE_OUTPUT_FILE, OUTPUT_FILE)
            shutil.copyfile(SAMPLE_MAPPING_FILE, OCCUPATION_MAPPING_FILE)
        else:
            logging.error("Arquivos de amostra não encontrados.")
        return

    try:
        df_astro = _load_feature_dataframe()
        logging.info("Linhas carregadas: %s", len(df_astro))

        # Remover linhas com valores nulos críticos (ex: sem nome ou ocupação)
        df_astro.dropna(subset=['name', 'occupation'], inplace=True)
        logging.info(f"Linhas após remover nulos críticos: {len(df_astro)}")

        # Separar features (X) e target (y)
        X = df_astro.drop(columns=['name', 'occupation'])
        y = df_astro['occupation']

        # Codificar a variável alvo (profissão)
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)
        df_astro['occupation_encoded'] = y_encoded

        # Salvar o mapeamento do LabelEncoder para uso futuro
        with open(OCCUPATION_MAPPING_FILE, 'w') as f:
            json.dump(list(label_encoder.classes_), f)
        logging.info(f"Mapeamento de profissões salvo em {OCCUPATION_MAPPING_FILE}")

        # Preparar os dados (tratamento de nulos, codificação)
        X_prepared = prepare_data(X)

        # Juntar X e y novamente para salvar
        df_prepared = pd.concat([df_astro[['name', 'occupation', 'occupation_encoded']], X_prepared], axis=1)

        df_prepared.to_csv(OUTPUT_FILE, index=False)
        logging.info(f"Dados preparados e salvos em {OUTPUT_FILE}. Dimensões: {df_prepared.shape}")

    except FileNotFoundError:
        logging.error(f"Erro: O arquivo {INPUT_FILE} não foi encontrado.")
        if SAMPLE_OUTPUT_FILE.exists() and SAMPLE_MAPPING_FILE.exists():
            logging.info("Copiando arquivos de amostra para uso imediato.")
            pd.read_csv(SAMPLE_OUTPUT_FILE).to_csv(OUTPUT_FILE, index=False)
            with open(SAMPLE_MAPPING_FILE, 'r') as sample_fp, open(OCCUPATION_MAPPING_FILE, 'w') as target_fp:
                target_fp.write(sample_fp.read())
    except Exception as e:
        logging.error(f"Ocorreu um erro durante a preparação dos dados: {e}")
        logging.error(traceback.format_exc())
        if SAMPLE_OUTPUT_FILE.exists() and SAMPLE_MAPPING_FILE.exists():
            logging.info("Recuperando arquivos de amostra devido ao erro encontrado.")
            pd.read_csv(SAMPLE_OUTPUT_FILE).to_csv(OUTPUT_FILE, index=False)
            with open(SAMPLE_MAPPING_FILE, 'r') as sample_fp, open(OCCUPATION_MAPPING_FILE, 'w') as target_fp:
                target_fp.write(sample_fp.read())


if __name__ == '__main__':
    main()

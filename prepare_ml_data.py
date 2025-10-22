import pandas as pd
import json
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.model_selection import train_test_split
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

input_file = 'astrological_features.csv'
output_file = 'prepared_ml_data.csv'
occupation_mapping_file = 'occupation_label_mapping.json'

def prepare_data(df):
    # Preencher valores ausentes para colunas categóricas com 'Unknown'
    categorical_cols = [col for col in df.columns if 'sign' in col or 'element' in col or 'modality' in col]
    for col in categorical_cols:
        df[col] = df[col].fillna('Unknown')

    # Preencher valores ausentes para colunas numéricas (casas) com 0 ou -1 (indicando desconhecido)
    numeric_cols = [col for col in df.columns if 'house' in col]
    for col in numeric_cols:
        df[col] = df[col].fillna(0) # Usar 0 para indicar casa desconhecida

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

if __name__ == '__main__':
    try:
        df_astro = pd.read_csv(input_file)
        logging.info(f"Dados carregados do arquivo: {input_file}. Linhas: {len(df_astro)}")

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
        with open(occupation_mapping_file, 'w') as f:
            json.dump(list(label_encoder.classes_), f)
        logging.info(f"Mapeamento de profissões salvo em {occupation_mapping_file}")

        # Preparar os dados (tratamento de nulos, codificação)
        X_prepared = prepare_data(X)
        
        # Juntar X e y novamente para salvar
        df_prepared = pd.concat([df_astro[['name', 'occupation', 'occupation_encoded']], X_prepared], axis=1)

        df_prepared.to_csv(output_file, index=False)
        logging.info(f"Dados preparados e salvos em {output_file}. Dimensões: {df_prepared.shape}")

    except FileNotFoundError:
        logging.error(f"Erro: O arquivo {input_file} não foi encontrado.")
    except Exception as e:
        logging.error(f"Ocorreu um erro durante a preparação dos dados: {e}")
        logging.error(traceback.format_exc())

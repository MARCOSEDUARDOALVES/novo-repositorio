import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import json
import logging
import traceback
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

input_file = 'prepared_ml_data.csv'
occupation_mapping_file = 'occupation_label_mapping.json'
model_output_file = 'random_forest_model.pkl'

def develop_model():
    try:
        df_prepared = pd.read_csv(input_file)
        logging.info(f"Dados preparados carregados do arquivo: {input_file}. Dimensões: {df_prepared.shape}")

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
        joblib.dump(model, model_output_file)
        logging.info(f"Modelo salvo em {model_output_file}")

        # Fazer previsões no conjunto de teste
        y_pred = model.predict(X_test)

        # Avaliar o modelo
        accuracy = accuracy_score(y_test, y_pred)
        logging.info(f"Acurácia do modelo: {accuracy:.4f}")

        # Carregar o mapeamento de profissões completo
        with open(occupation_mapping_file, 'r') as f:
            full_occupation_labels = json.load(f)
        
        # Obter as classes presentes no conjunto de teste e suas respectivas labels
        unique_test_labels = sorted(y_test.unique())
        target_names_for_report = [full_occupation_labels[i] for i in unique_test_labels]

        # Gerar relatório de classificação
        report = classification_report(y_test, y_pred, labels=unique_test_labels, target_names=target_names_for_report, zero_division=0)
        logging.info("Relatório de Classificação:\n" + report)

        return model, accuracy, report

    except FileNotFoundError:
        logging.error(f"Erro: O arquivo {input_file} ou {occupation_mapping_file} não foi encontrado.")
        return None, None, None
    except Exception as e:
        logging.error(f"Ocorreu um erro durante o desenvolvimento do modelo: {e}")
        logging.error(traceback.format_exc())
        return None, None, None

if __name__ == '__main__':
    develop_model()

'''
Este script carrega o modelo de classificação de profissões treinado, 
analisa a importância das características e visualiza os resultados para 
ajudar na interpretação do desempenho do modelo.
'''
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Caminhos dos arquivos
MODEL_FILE = 'random_forest_model.pkl'
PREPARED_DATA_FILE = 'prepared_ml_data.csv'

def analyze_model():
    '''
    Carrega o modelo treinado e os dados preparados para analisar a importância 
    das características e visualizar os resultados.
    '''
    try:
        # Carregar o modelo treinado
        model = joblib.load(MODEL_FILE)
        logging.info(f"Modelo carregado de {MODEL_FILE}")

        # Carregar os dados preparados para obter os nomes das características
        df_prepared = pd.read_csv(PREPARED_DATA_FILE)
        feature_names = df_prepared.drop(columns=['name', 'occupation', 'occupation_encoded']).columns

        # Obter a importância das características
        feature_importances = model.feature_importances_

        # Criar um DataFrame para facilitar a análise
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': feature_importances
        }).sort_values(by='importance', ascending=False)

        logging.info("Top 20 características mais importantes:")
        logging.info(importance_df.head(20))

        # Visualizar a importância das características
        plt.figure(figsize=(12, 8))
        sns.barplot(x='importance', y='feature', data=importance_df.head(20), palette='viridis')
        plt.title('Top 20 Características Mais Importantes')
        plt.xlabel('Importância')
        plt.ylabel('Característica')
        plt.tight_layout()
        plt.savefig('feature_importance.png')
        logging.info("Gráfico de importância das características salvo em feature_importance.png")

    except FileNotFoundError:
        logging.error(f"Erro: O arquivo {MODEL_FILE} ou {PREPARED_DATA_FILE} não foi encontrado.")
    except Exception as e:
        logging.error(f"Ocorreu um erro durante a análise do modelo: {e}")

if __name__ == '__main__':
    analyze_model()


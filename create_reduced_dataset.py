import pandas as pd

# Caminho para o arquivo CSV original
input_file = 'pantheon_cleaned_data.csv'
# Caminho para o novo arquivo CSV com 1000 registros
output_file = 'pantheon_reduced_1000.csv'

try:
    # Ler o arquivo CSV original
    df = pd.read_csv(input_file)
    
    # Selecionar os primeiros 1000 registros
    df_reduced = df.head(1000)
    
    # Salvar o subconjunto em um novo arquivo CSV
    df_reduced.to_csv(output_file, index=False)
    
    print(f"Subconjunto de 1000 registros criado com sucesso em {output_file}")
except FileNotFoundError:
    print(f"Erro: O arquivo {input_file} não foi encontrado.")
except Exception as e:
    print(f"Ocorreu um erro: {e}")

Para utilizar o controle de versão Git neste projeto, siga os passos abaixo:
    Após a instalação, abra o terminal e configure suas informações:
    ```
    git config --global user.name "Seu Nome"
    git config --global user.email "seu.email@exemplo.com"
    ```
 
 3. **Inicialize o repositório**:
    No diretório do projeto, execute:
    ```
    git init
    ```
 
 4. **Primeiro commit**:
    ```
    git add .
    git commit -m "Commit inicial"
    ```
 
 ## Estrutura do Projeto
 
 Este projeto contém:
 - Arquivos Python para processamento de dados astrológicos
 - Interface web em React (App.jsx)
 - Ferramentas para análise de dados
 
-## Como Executar o Projeto
+## Dados de exemplo incluídos
 
-[Adicione instruções específicas para executar seu projeto aqui]
\ No newline at end of file
+Para facilitar a execução local sem necessidade de baixar bases externas, o repositório inclui um conjunto pequeno de dados astrológicos fictícios na pasta `data/`. Esses arquivos permitem percorrer todo o pipeline mesmo em ambientes sem acesso à internet ou sem bibliotecas científicas instaladas.
+
+Principais arquivos de exemplo:
+
+| Arquivo | Descrição |
+| --- | --- |
+| `data/sample_person_2025_update.csv` | Amostra com dados biográficos básicos (nome, ocupação, data e local de nascimento). |
+| `data/sample_pantheon_cleaned_data.csv` | Versão higienizada pronta para criação do subconjunto reduzido. |
+| `data/sample_astrological_features.csv` | Características astrológicas já calculadas para seis personalidades. |
+| `data/sample_prepared_ml_data.csv` | Base vetorizada pronta para treinamento do modelo. |
+| `data/sample_random_forest_model.pkl` | Modelo "stub" treinado sobre os dados de exemplo com métricas pré-calculadas. |
+
+Os scripts Python detectam automaticamente essas amostras quando os arquivos reais não estão presentes ou quando dependências (como `pandas`, `scikit-learn`, `immanuel` ou `swisseph`) não estão instaladas. Dessa forma, a execução gera/copias os resultados a partir das amostras mantendo a experiência consistente.
+
+## Como Executar o Pipeline de Machine Learning
+
+1. **Limpeza dos dados brutos**
+   ```bash
+   python process_pantheon_data.py
+   ```
+   - Se `pandas` estiver instalado e o arquivo `person_2025_update.csv` existir, o script limpará os dados reais e salvará `pantheon_cleaned_data.csv`.
+   - Caso contrário, a versão de amostra (`data/sample_pantheon_cleaned_data.csv`) será copiada automaticamente para o local esperado.
+
+2. **Criação do subconjunto reduzido**
+   ```bash
+   python create_reduced_dataset.py
+   ```
+   - Com dependências disponíveis, será gerado `pantheon_reduced_1000.csv`.
+   - Sem dependências, a amostra correspondente é reutilizada.
+
+3. **Geração de características astrológicas**
+   ```bash
+   python generate_astro_features.py
+   ```
+   - Se `immanuel`, `swisseph` e `pandas` estiverem presentes, as cartas natais são calculadas.
+   - Do contrário, `astrological_features.csv` é preenchido com os dados de amostra.
+
+4. **Preparação dos dados para ML**
+   ```bash
+   python prepare_ml_data.py
+   ```
+   - Com `pandas` e `scikit-learn`, ocorre a vetorização e geração de `prepared_ml_data.csv` + `occupation_label_mapping.json`.
+   - Sem esses pacotes, os arquivos prontos são copiados de `data/`.
+
+5. **Treinamento (ou carregamento) do modelo**
+   ```bash
+   python develop_ml_model.py
+   ```
+   - Quando todas as dependências estão disponíveis, um `RandomForestClassifier` é treinado e salvo em `random_forest_model.pkl`.
+   - Na ausência de bibliotecas de ML, o modelo de amostra é copiado e os relatórios pré-calculados são retornados.
+
+> **Dica:** os arquivos `astrological_features.csv`, `prepared_ml_data.csv` e `random_forest_model.pkl` já estão versionados na raiz do projeto para uso imediato.
+
+### Pacote pronto para envio
+
+Se preferir receber todos os artefatos resultantes sem executar nenhum script, utilize o utilitário `export_offline_results.py`:
+
+```bash
+python export_offline_results.py --zip
+```
+
+O comando acima copia os arquivos gerados do pipeline para a pasta `offline_results/`, cria um `manifest.json` com a descrição de cada item e monta o arquivo `offline_bundle.zip`, pronto para ser compartilhado.
+
+## Dependências opcionais
+
+Para substituir os dados de amostra por informações reais, instale as seguintes bibliotecas:
+
+- `pandas`
+- `scikit-learn`
+- `immanuel` + `swisseph` (para cálculo de cartas natais)
+
+Após a instalação, coloque seus arquivos reais (`person_2025_update.csv`, etc.) no diretório raiz e execute os scripts na ordem acima.
 
EOF
)
Atualização inicial pelo Codex - qua, 22 de out de 2025 20:53:30

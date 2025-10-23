# Projeto MADELAINE

## Configuração do Git

Para utilizar o controle de versão Git neste projeto, siga os passos abaixo:

1. **Instale o Git**:
   - Baixe o Git em [https://git-scm.com/downloads](https://git-scm.com/downloads)
   - Siga as instruções de instalação para o seu sistema operacional
   - Certifique-se de selecionar a opção para adicionar o Git ao PATH do sistema

2. **Configure suas credenciais**:
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

5. **Conecte ao GitHub**:
   - Crie (ou localize) o repositório remoto e copie a URL HTTPS.
   - Adicione o remoto `origin`:
     ```
     git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
     ```
   - Verifique com `git remote -v` se a URL está configurada.
   - Envie a branch atual e registre o upstream:
     ```
     git push -u origin work
     ```
   - Se estiver rodando em um ambiente restrito (como este sandbox do Codex), operações de rede podem falhar com erro `CONNECT tunnel failed, response 403`. Nesse caso, faça o `git push` a partir da sua máquina local: copie o repositório para o computador, adicione o mesmo remoto e execute os comandos acima com suas credenciais.

## Sequência rápida de comandos (Git Bash)

Os passos abaixo já estão ajustados para o seu repositório
`https://github.com/MARCOSEDUARDOALVES/novo-repositorio` e podem ser
copiados diretamente para o Git Bash:

```bash
# 1. (Opcional) Crie uma pasta de trabalho e acesse-a
mkdir -p ~/Downloads/novo-repositorio-transfer && cd ~/Downloads/novo-repositorio-transfer

# 2. Converta o bundle Base64 que você copiou do Codex
base64 -d work.bundle.b64.txt > work.bundle

# 3. Restaure o histórico da branch work a partir do bundle
git clone work.bundle novo-repositorio
cd novo-repositorio
git checkout work

# 4. Conecte ao seu GitHub e envie a branch
git remote add origin https://github.com/MARCOSEDUARDOALVES/novo-repositorio.git
git push -u origin work

# 5. (Depois de novas alterações) Comitar e publicar novamente
git add .
git commit -m "Mensagem explicando a atualização"
git push
```

Esses comandos assumem que o arquivo `work.bundle.b64.txt` (ou o texto
copiado entre os marcadores `BEGIN/END REPO BUNDLE`) já está na pasta
em que você abriu o Git Bash. Caso tenha baixado também o
`worktree_snapshot.zip`, extraia-o após o `git checkout work` com
`unzip worktree_snapshot.zip -d .`.

### Passo a passo no Git Bash para atualizar o GitHub

Quando já existir um repositório no GitHub (por exemplo, `https://github.com/MARCOSEDUARDOALVES/novo-repositorio`), siga esta sequência **no Git Bash do seu computador** para enviar a branch `work` que veio do Codex:

1. Posicione-se na pasta onde deseja restaurar o projeto e cole o bundle transferido do Codex:
   ```bash
   base64 -d work.bundle.b64.txt > work.bundle
   git clone work.bundle novo-repositorio
   cd novo-repositorio
   git checkout work
   ```
2. Conecte o repositório local ao GitHub:
   ```bash
   git remote add origin https://github.com/MARCOSEDUARDOALVES/novo-repositorio.git
   git remote -v
   ```
   - Confirme que a URL correta aparece para `origin` em `fetch` e `push`.
3. Envie tudo para o GitHub e defina o *upstream* da branch `work`:
   ```bash
   git push -u origin work
   ```
4. A partir daí, sempre que fizer novas alterações no seu computador, basta repetir:
   ```bash
   git add .
   git commit -m "Mensagem explicando a atualização"
   git push
   ```

Esse fluxo garante que todo o histórico produzido aqui seja recriado localmente e enviado ao GitHub usando apenas comandos do Git Bash.

## Executar a aplicação web e gerar um link de acesso

O projeto possui um servidor Express que entrega os arquivos estáticos (React/Vite
build) e imprime automaticamente os links acessíveis assim que for iniciado. O
passo a passo abaixo funciona no Windows (Git Bash), macOS ou Linux:

1. **Instale o Node.js 18 ou superior**
   - Baixe em [https://nodejs.org/](https://nodejs.org/) e conclua a instalação.
   - Reinicie o terminal após a instalação para garantir que `node` e `npm`
     estejam disponíveis.

2. **Instale as dependências do projeto**
   ```bash
   cd caminho/para/novo-repositorio
   npm install
   ```

3. **Inicie o servidor Express**
   ```bash
   npm run start
   ```
   - O comando utiliza `server.mjs` para servir `index.html` e os demais ativos.
   - No terminal será exibido `Servidor rodando em http://localhost:3000`.
   - O servidor também lista automaticamente todos os endereços IPv4 da sua
     máquina na mesma rede (por exemplo, `http://192.168.0.10:3000`). Esses são
     os links que podem ser abertos em outro computador ou celular conectado à
     mesma rede Wi-Fi.

4. **(Opcional) Executar o front-end em modo desenvolvimento (Vite)**
  ```bash
  npm run dev
  ```
  - O comando já inicia o Vite em `http://localhost:5173/`, abre o navegador
    automaticamente e permite acesso externo pela rede local (`http://seu-ip:5173/`).
  - Use esse modo quando quiser *hot reload* no React enquanto modifica os
    arquivos `App.jsx`, `App.css` ou demais componentes.
  - Se quiser continuar usando o servidor Express com recarregamento automático,
    utilize `npm run dev:server`.

> ⚠️ **Erro `npm ERR! enoent ... package.json`**
>
> Esse erro indica que o terminal não está dentro da pasta do projeto quando o
> comando `npm run dev` é executado. Antes de rodar qualquer script do `npm`,
> confirme que o caminho atual contém `package.json`:
>
> ```bash
> pwd            # mostra a pasta atual
> ls             # verifique se package.json aparece na lista
> cd caminho/para/novo-repositorio
> npm install
> npm run dev
> ```
>
> No Git Bash do Windows, a pasta costuma ser algo como
> `cd ~/Downloads/novo-repositorio`. Depois do `cd`, repita `ls` e confira que
> arquivos como `package.json` e `App.jsx` estão visíveis; só então execute os
> comandos do Vite.

5. **Encerrar o servidor**
   - Pressione `Ctrl + C` no terminal para finalizar.

> 💡 Caso queira tornar o link acessível fora da sua rede local, utilize um túnel
> seguro (por exemplo, [ngrok](https://ngrok.com/) ou o serviço de hospedagem de
> sua preferência) apontando para a porta exibida pelo servidor (`3000` por
> padrão).

### Se o GitHub mostrar "O Codex atualmente não permite atualizar PRs"

Algumas vezes, ao abrir um Pull Request criado a partir deste ambiente, o botão
**Update branch** no GitHub exibe a mensagem:

> `O Codex atualmente não permite atualizar PRs que foram modificados fora dele. Por enquanto, crie um novo PR.`

Essa é uma limitação da plataforma: o histórico gerado aqui precisa ser enviado
do **seu computador** e um novo PR deve ser criado manualmente. Para atualizar a
branch mesmo assim:

1. Siga o passo a passo acima para restaurar o bundle no Git Bash e execute `git push -u origin work`.
2. No GitHub, acesse o repositório (`https://github.com/MARCOSEDUARDOALVES/novo-repositorio`).
3. Clique em **Pull requests ▸ New pull request**.
4. Garanta que o campo **base** esteja em `main` (ou na branch de destino desejada) e **compare** em `work`.
5. Revise o diff, escreva o título/descrição e finalize com **Create pull request**.

Após esse push feito a partir da sua máquina, a branch `work` estará atualizada
no GitHub, e o novo PR refletirá todos os commits vindos do Codex. Caso existisse
um PR anterior aberto pelo sandbox, você pode fechá-lo ou mantê-lo apenas como
histórico.

## Exportar o repositório quando o push não funciona

Caso não consiga baixar os arquivos diretamente ou conectar-se ao GitHub a partir do sandbox, gere um pacote completo da branch `work` com:

```bash
python export_repository_bundle.py --skip-zip --print-base64 --base64-output transfer/work.bundle.b64.txt
```

O script cria arquivos na pasta `transfer/`:

- `transfer/work.bundle`: contém todo o histórico Git (commits, branches, tags). 
- `transfer/work.bundle.b64.txt`: texto pronto para ser copiado/transferido caso você só possa mover conteúdo via copiar/colar. Este arquivo já está versionado no repositório para facilitar o download direto.
- (Opcional) `transfer/worktree_snapshot.zip`: remova o parâmetro `--skip-zip` se quiser gerar também o snapshot da árvore de trabalho.

Se não for possível baixar os arquivos produzidos, utilize o arquivo `transfer/work.bundle.b64.txt` (ou copie o bloco Base64 exibido pelo script) e converta com `base64 -d`. Em seguida, você pode clonar a partir do bundle e enviar tudo para o GitHub normalmente. Consulte `transfer/README.md` para ver o passo a passo completo de restauração.

### Passo a passo rápido para restaurar no seu computador

1. **Use o arquivo Base64 pronto** (`transfer/work.bundle.b64.txt`) ou copie manualmente a saída mostrada entre os marcadores `-----BEGIN REPO BUNDLE-----` e `-----END REPO BUNDLE-----` para um arquivo local.
2. **Converta o arquivo** para o formato binário do bundle:
   ```bash
   base64 -d work.bundle.b64.txt > work.bundle
   ```
3. **Clone o bundle** para reconstruir o histórico da branch `work`:
   ```bash
   git clone work.bundle novo-repositorio
   cd novo-repositorio
   git checkout work
   ```
4. **(Opcional) Restaure o snapshot da árvore de trabalho** caso tenha copiado também `transfer/worktree_snapshot.zip`:
   ```bash
   unzip worktree_snapshot.zip -d novo-repositorio
   ```
5. **Conecte ao seu GitHub e envie os commits**:
   ```bash
   git remote add origin https://github.com/MARCOSEDUARDOALVES/novo-repositorio.git
   git push -u origin work
   ```

Esses passos garantem que todo o histórico produzido aqui no Codex seja recriado no seu computador e enviado ao GitHub mesmo que o sandbox não consiga se comunicar diretamente com o serviço remoto.

## Estrutura do Projeto

Este projeto contém:
- Arquivos Python para processamento de dados astrológicos
- Interface web em React (App.jsx)
- Ferramentas para análise de dados

## Dados de exemplo incluídos

Para facilitar a execução local sem necessidade de baixar bases externas, o repositório inclui um conjunto pequeno de dados astrológicos fictícios na pasta `data/`. Esses arquivos permitem percorrer todo o pipeline mesmo em ambientes sem acesso à internet ou sem bibliotecas científicas instaladas.

Principais arquivos de exemplo:

| Arquivo | Descrição |
| --- | --- |
| `data/sample_person_2025_update.csv` | Amostra com dados biográficos básicos (nome, ocupação, data e local de nascimento). |
| `data/sample_pantheon_cleaned_data.csv` | Versão higienizada pronta para criação do subconjunto reduzido. |
| `data/sample_astrological_features.csv` | Características astrológicas já calculadas (signo, casa, elemento, modalidade, aspectos, graus, dispositores tradicional/moderno **e métricas de temperamento**) para seis personalidades. |
| `data/sample_prepared_ml_data.csv` | Base vetorizada pronta para treinamento do modelo, incluindo os vetores derivados dos graus planetários, dispositores e agregados de temperamento. |
| `data/sample_model_metrics.json` | Métricas de referência para o modelo de amostra utilizado nas saídas offline. |

Os scripts Python detectam automaticamente essas amostras quando os arquivos reais não estão presentes ou quando dependências (como `pandas`, `scikit-learn`, `immanuel` ou `swisseph`) não estão instaladas. Dessa forma, a execução gera/copias os resultados a partir das amostras mantendo a experiência consistente.

## Como Executar o Pipeline de Machine Learning

### 0. Habilite o banco de dados astrológico online (opcional, recomendado)

Defina as variáveis de ambiente para apontar para a API que disponibiliza os
registros astrológicos. Pelo menos `ASTRO_DB_BASE_URL` deve estar presente; as
demais permitem ajustar rotas específicas se a sua API utilizar caminhos
diferentes dos padrões:

```bash
export ASTRO_DB_BASE_URL="https://api.sua-plataforma-astrologica.com"
# Caso necessário, informe também:
export ASTRO_DB_API_KEY="seu_token"
export ASTRO_DB_PEOPLE_ENDPOINT="/people"
export ASTRO_DB_FEATURES_ENDPOINT="/astro-features"
export ASTRO_DB_PREPARED_ENDPOINT="/ml/prepared"
```

Se a conexão falhar ou as variáveis não estiverem definidas, o pipeline cai
automaticamente para os CSVs de amostra versionados no repositório, garantindo
execução offline.

1. **Limpeza dos dados brutos**
   ```bash
   python process_pantheon_data.py
   ```
   - Com o banco online habilitado, os registros são baixados via API e limpos
     antes de salvar `pantheon_cleaned_data.csv`.
   - Em caso de falha, o script procura `person_2025_update.csv` local e, não
     encontrando, reutiliza `data/sample_pantheon_cleaned_data.csv`.

2. **Criação do subconjunto reduzido**
   ```bash
   python create_reduced_dataset.py
   ```
   - Recupera até 1.000 entradas diretamente do banco astrológico para gerar
     `pantheon_reduced_1000.csv`.
   - Se o serviço estiver indisponível, o subconjunto de amostra é copiado.

3. **Geração de características astrológicas**
   ```bash
   python generate_astro_features.py
   ```
   - Quando `immanuel`, `swisseph` e `pandas` estão instalados, os dados reduzidos
     obtidos da API são usados para calcular as cartas natais reais.
   - Sem acesso ao banco ou às dependências opcionais, `astrological_features.csv`
     é preenchido com a amostra.
   - A saída inclui, para cada planeta pessoal e transpessoal, o signo, a casa, o
     elemento, a modalidade, a contagem de aspectos, **o grau e os dispositores
     tradicional e moderno** — recursos inspirados em autores clássicos e
     contemporâneos para identificar o propósito individual.

4. **Preparação dos dados para ML**
   ```bash
   python prepare_ml_data.py
   ```
   - Consulta as características diretamente no banco (`/astro-features`) para
     gerar `prepared_ml_data.csv` e `occupation_label_mapping.json`.
   - Caso contrário, usa os CSVs locais ou de amostra.

5. **Treinamento (ou carregamento) do modelo**
   ```bash
   python develop_ml_model.py
   ```
   - Com todas as dependências disponíveis, treina o `RandomForestClassifier`
     usando os vetores vindos da API (`/ml/prepared` por padrão).
   - Na ausência de bibliotecas de ML ou do banco online, gera um modelo
     fictício com base nos samples (`data/sample_model_metrics.json`, etc.).

> **Dica:** os arquivos `astrological_features.csv` e `prepared_ml_data.csv` já estão versionados na raiz do projeto para uso imediato. O arquivo `random_forest_model.pkl` é gerado sob demanda pelo script para evitar problemas com anexos binários em provedores Git.

### Parâmetros astrológicos considerados

O pipeline dá atenção especial aos indicadores associados ao propósito e à vocação segundo a literatura de referência em astrologia psicológica e tradicional:

- **Graus e dispositores** dos dez planetas principais (Sol, Lua, Mercúrio, Vênus, Marte, Júpiter, Saturno, Urano, Netuno e Plutão). Os graus permitem medir a atuação precisa em cada signo/casa, enquanto os dispositores tradicional e moderno contextualizam o “senhor” daquele posicionamento conforme autores clássicos (Ptolomeu, Lilly) e modernos (Dane Rudhyar, Liz Greene, Stephen Arroyo).
- **Elementos dos dispositores (Fogo, Terra, Ar, Água)** para mapear em qual qualidade energética os dispositores tradicional e moderno se expressam, incluindo contagens agregadas e identificação dos elementos dominantes de cada fluxo dispositor.
- **Signo, elemento e modalidade** para capturar a expressão energética de cada planeta.
- **Casas astrológicas** para relacionar as áreas de manifestação prática.
- **Aspectos principais** (representados pela contagem agregada) para oferecer sinais de integração ou tensão entre planetas.
- **Temperamentos astrológicos** calculados segundo a combinação de elementos e dispositores (tradição x modernidade), entregando contagens para os quatro tipos fundamentais (colérico, sanguíneo, melancólico e fleumático), além da identificação do temperamento dominante com sugestões de profissões e desafios descritos por autores de referência.

Esses indicadores de temperamento utilizam a literatura de grandes astrólogos (do renascentista Marsilio Ficino aos psicólogos-astrólogos modernos) para mapear o fluxo dispositor-planeta e enriquecer a análise vocacional com propensões, talentos e ajustes necessários.

Esses parâmetros alimentam o conjunto vetorizado em `prepared_ml_data.csv`, permitindo que o modelo de machine learning considere os circuitos de dispositores e a ênfase por graus na avaliação do propósito individual.

### Pacote pronto para envio

Se preferir receber todos os artefatos resultantes sem executar nenhum script, utilize o utilitário `export_offline_results.py`:

```bash
python export_offline_results.py
```

O comando copia os arquivos gerados do pipeline para a pasta `offline_results/`, cria um `manifest.json` com a descrição de cada item **e** monta automaticamente o arquivo `offline_bundle.zip`, pronto para ser compartilhado localmente. Para manter o repositório livre de binários pesados, o `.zip` não é mais versionado; gere-o sempre que precisar compartilhar os resultados ou anexá-los a um PR. Use a opção `--no-zip` se quiser atualizar apenas os arquivos abertos sem recriar o ZIP.

## Dependências opcionais

Para explorar dados reais diretamente da sua API, instale as bibliotecas abaixo
e configure as variáveis `ASTRO_DB_*`. Se preferir trabalhar com arquivos
locais, ainda é possível substituir os samples manualmente:

- `pandas`
- `scikit-learn`
- `immanuel` + `swisseph` (para cálculo de cartas natais)

Após a instalação, você pode optar por fornecer a API online (recomendado) ou
copiar arquivos reais (`person_2025_update.csv`, etc.) para o diretório raiz e
executar os scripts na ordem acima.

---
title: Mapa ERB Azimutes
emoji: 📡
colorFrom: blue
colorTo: gray
sdk: streamlit
app_file: app.py
pinned: false
---

# Mapa de ERBs e Azimutes

Aplicação Streamlit para visualizar estações rádio base (ERBs), seus setores de
cobertura e azimutes de antena sobre um mapa de satélite, com o objetivo de
identificar visualmente casos críticos de apontamento em relação a prédios de
referência. Acesso protegido por login.

## Executando localmente

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
streamlit run app.py
```

As credenciais de login ficam em `.streamlit/secrets.toml` (não versionado).
Use `.streamlit/secrets.toml.example` como modelo. Para gerar o hash de uma
nova senha:

```bash
python gerar_hash_senha.py
```

> O usuário padrão incluído neste ambiente local é `admin` / `admin`. **Troque
> essa senha antes de usar o app com dados reais**, especialmente após o
> deploy público.

## Dados de entrada

- **CSV de licenciamento (obrigatório)**: exportação do Mosaico/ANATEL,
  separador `|`, com colunas `Latitude`, `Longitude`, `Azimute`,
  `AnguloMeiaPotenciaAntena` e, opcionalmente, `NumEstacao`, `NomeEntidade`,
  `Tecnologia`, `Municipio.NomeMunicipio`, `EnderecoEstacao`.
- **CSV de correções (opcional)**: colunas `NumEstacao`, `Latitude`,
  `Longitude`, para sobrescrever coordenadas de estações específicas.
- **CSV de prédios de referência (opcional)**: colunas de latitude/longitude,
  usados apenas como marcadores visuais (alvo em vermelho, não-alvo em
  verde) para apoiar a identificação visual de casos críticos.

## Versão standalone (arquivo HTML único)

[`mapa_portatil.html`](mapa_portatil.html) é uma versão independente, sem
Python/Streamlit: HTML + JavaScript puro (Leaflet + PapaParse via CDN), com a
mesma lógica de setores/azimutes. Basta baixar esse arquivo e abrir com
duplo clique em qualquer PC com navegador e internet (os mapas de satélite
são carregados via CDN/Google, então precisa de conexão).

Diferença importante: **não tem login de servidor**. Existe apenas uma trava
de senha local em JavaScript (padrão `admin`), que serve só para evitar
abertura casual — qualquer pessoa com acesso ao arquivo pode ver o
código-fonte e extrair/trocar a senha. Para trocar a senha, gere um novo
hash SHA-256 e substitua a constante `SENHA_HASH_SHA256` no arquivo:

```bash
python -c "import hashlib; print(hashlib.sha256('sua-nova-senha'.encode()).hexdigest())"
```

## Deploy no Streamlit Community Cloud

1. Suba este repositório para o GitHub (já feito, se você seguiu o fluxo
   completo).
2. Acesse https://share.streamlit.io, conecte sua conta GitHub e escolha este
   repositório + branch `main` + arquivo `app.py`.
3. Em **Advanced settings → Secrets**, cole o conteúdo do seu
   `.streamlit/secrets.toml` local (com os hashes reais de senha).
4. Clique em **Deploy**.

## Deploy no Hugging Face Spaces (alternativa)

Se a conta do Streamlit Community Cloud estiver bloqueada/indisponível, o
mesmo app roda em um [Space](https://huggingface.co/spaces) do Hugging Face
(free tier), usando este mesmo repositório.

1. Crie uma conta em https://huggingface.co (se ainda não tiver) e gere um
   **Access Token** (tipo *Write*) em
   https://huggingface.co/settings/tokens.
2. Instale a CLI e faça login (cole o token quando pedir):
   ```bash
   pip install huggingface_hub
   huggingface-cli login
   ```
3. Crie um Space em https://huggingface.co/new-space com:
   - SDK: **Streamlit**
   - Visibilidade: pública ou privada, como preferir
4. Adicione o Space como um segundo remote git deste repositório e envie o
   código (o `README.md` já tem o front-matter que o Hugging Face exige):
   ```bash
   git remote add space https://huggingface.co/spaces/SEU_USUARIO/NOME_DO_SPACE
   git push space main
   ```
5. No painel do Space, vá em **Settings → Variables and secrets** e
   adicione como *secret*:
   - `ADMIN_PASSWORD_HASH`: o hash bcrypt da senha (gerado com
     `python gerar_hash_senha.py`)
   - `COOKIE_KEY`: uma string aleatória longa (`python -c "import secrets; print(secrets.token_hex(32))"`)
   - Opcionalmente `COOKIE_NAME` e `COOKIE_EXPIRY_DAYS`

   (O `app.py` já sabe ler essas variáveis de ambiente quando não há
   `st.secrets` configurado, então não é preciso tocar no código.)
6. O Space reconstrói e publica automaticamente após o push e a definição
   dos secrets.

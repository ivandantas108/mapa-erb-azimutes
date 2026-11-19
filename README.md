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

## Deploy no Streamlit Community Cloud

1. Suba este repositório para o GitHub (já feito, se você seguiu o fluxo
   completo).
2. Acesse https://share.streamlit.io, conecte sua conta GitHub e escolha este
   repositório + branch `main` + arquivo `app.py`.
3. Em **Advanced settings → Secrets**, cole o conteúdo do seu
   `.streamlit/secrets.toml` local (com os hashes reais de senha).
4. Clique em **Deploy**.

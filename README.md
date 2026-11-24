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

## Deploy no Hugging Face Spaces (ativo)

A Hugging Face passou a cobrar assinatura PRO para Spaces do tipo `docker`
ou `gradio`; apenas o tipo `static` (HTML/JS puro, sem servidor) continua
gratuito. Por isso, o que está publicado lá é a **versão standalone**
([`mapa_portatil.html`](mapa_portatil.html)), enviada como `index.html` de
um Space estático:

**https://huggingface.co/spaces/ivandantas108/mapa-erb-azimutes**
(direto: https://ivandantas108-mapa-erb-azimutes.static.hf.space/)

Senha de acesso: `admin` (trava local em JavaScript, não é login de
servidor — ver limitações na seção "Versão standalone" acima).

Para atualizar o Space após mudar `mapa_portatil.html`:
```bash
pip install huggingface_hub
python -c "
from huggingface_hub import HfApi
api = HfApi()  # usa o login feito via 'huggingface-cli login'
api.upload_file(
    path_or_fileobj='mapa_portatil.html',
    path_in_repo='index.html',
    repo_id='ivandantas108/mapa-erb-azimutes',
    repo_type='space',
)
"
```

Se no futuro você assinar o Hugging Face PRO e quiser o `app.py` completo
(com login de servidor de verdade) rodando lá, este repositório já inclui
um [`Dockerfile`](Dockerfile) pronto: basta recriar o Space com
`space_sdk='docker'` e dar `git push` deste repositório para o remote do
Space.

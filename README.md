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

## Publicar com um clique (link público temporário)

[`publicar_app.bat`](publicar_app.bat) automatiza tudo: cria o `venv` se
não existir, instala as dependências, gera um login padrão (`admin`/`admin`)
se este PC nunca rodou o app, instala o `cloudflared` se necessário, sobe a
aplicação e abre um **túnel público** (Cloudflare) até ela.

Basta copiar a pasta do projeto para qualquer PC Windows com Python
instalado e dar duplo clique em `publicar_app.bat`. Ao final, ele imprime
(e já copia para a área de transferência) um link do tipo
`https://palavras-aleatorias.trycloudflare.com`, acessível de qualquer
computador em qualquer rede.

Pré-requisitos: Python instalado e no PATH
(https://www.python.org/downloads/, marcando "Add python.exe to PATH").
O resto (`cloudflared`) o script tenta instalar sozinho via `winget`.

Pontos importantes:
- O link muda a cada execução (é um túnel novo toda vez).
- Só funciona enquanto a janela ficar aberta e o PC não suspender/hibernar
  nem perder internet — fechar a janela encerra tudo.
- Esse caminho usa o `app.py` de verdade, com login de servidor real
  (diferente da versão standalone HTML abaixo).

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

## Deploy no Hugging Face Spaces (ativo)

O que está publicado lá é a **versão standalone**
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


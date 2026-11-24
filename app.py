import os

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import streamlit.components.v1 as components

from erb_map import (
    aplicar_correcoes_coordenadas,
    carregar_csv_licenciamento,
    construir_mapa,
)

st.set_page_config(page_title="Mapa de ERBs e Azimutes", layout="wide")


def _para_dict_puro(valor):
    """Converte recursivamente objetos Secrets/AttrDict do Streamlit em dict/list comuns."""
    if hasattr(valor, "items"):
        return {chave: _para_dict_puro(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_para_dict_puro(item) for item in valor]
    return valor


def _config_credenciais():
    """Lê credenciais de st.secrets (Streamlit Cloud/local) ou, na ausência,
    de variáveis de ambiente (Hugging Face Spaces usa 'Repository secrets' como env vars)."""
    try:
        credenciais = _para_dict_puro(st.secrets["credentials"])
        cookie_cfg = dict(st.secrets["cookie"])
        return credenciais, cookie_cfg
    except Exception:
        pass

    senha_hash = os.environ.get("ADMIN_PASSWORD_HASH")
    cookie_key = os.environ.get("COOKIE_KEY")
    if not senha_hash or not cookie_key:
        st.error(
            "Configuração de login ausente. Defina os secrets "
            "`credentials`/`cookie` (Streamlit) ou as variáveis de ambiente "
            "`ADMIN_PASSWORD_HASH` e `COOKIE_KEY` (Hugging Face Spaces)."
        )
        st.stop()

    credenciais = {"usernames": {"admin": {"name": "Administrador", "password": senha_hash}}}
    cookie_cfg = {
        "name": os.environ.get("COOKIE_NAME", "mapa_erb_auth"),
        "key": cookie_key,
        "expiry_days": float(os.environ.get("COOKIE_EXPIRY_DAYS", "30")),
    }
    return credenciais, cookie_cfg


def carregar_autenticador():
    credenciais, cookie_cfg = _config_credenciais()
    return stauth.Authenticate(
        credenciais,
        cookie_cfg["name"],
        cookie_cfg["key"],
        cookie_cfg["expiry_days"],
        auto_hash=False,
    )


authenticator = carregar_autenticador()
authenticator.login(location="main")

if st.session_state.get("authentication_status") is False:
    st.error("Usuário ou senha incorretos.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Informe usuário e senha para acessar.")
    st.stop()

# authentication_status is True a partir daqui
with st.sidebar:
    st.write(f"Usuário: **{st.session_state['name']}**")
    authenticator.logout("Sair", location="sidebar")

st.title("Mapa de Estações Rádio Base (ERBs) e Azimutes")
st.caption(
    "Visualize estações, setores de cobertura e azimutes das antenas para identificar "
    "casos críticos de apontamento em relação a prédios de referência."
)

st.sidebar.header("Dados de entrada")
arquivo_csv = st.sidebar.file_uploader(
    "CSV de licenciamento (ANATEL, separador '|')", type=["csv"]
)

with st.sidebar.expander("Opcional: correções de coordenadas"):
    st.caption("CSV com colunas NumEstacao, Latitude, Longitude para sobrescrever coordenadas incorretas.")
    arquivo_correcoes = st.file_uploader("CSV de correções", type=["csv"], key="correcoes")

with st.sidebar.expander("Opcional: prédios de referência"):
    st.caption("CSV com colunas de latitude/longitude. Usados apenas como marcadores visuais.")
    arquivo_alvo = st.file_uploader("Prédios alvo (marcados em vermelho)", type=["csv"], key="alvo")
    arquivo_nao_alvo = st.file_uploader("Prédios não-alvo (marcados em verde)", type=["csv"], key="nao_alvo")

raio_metros = st.sidebar.slider("Raio do setor (m)", min_value=20, max_value=1000, value=100, step=10)
usar_satelite = st.sidebar.checkbox("Usar imagem de satélite como base", value=True)

if not arquivo_csv:
    st.info("Envie o CSV de licenciamento na barra lateral para gerar o mapa.")
    st.stop()

try:
    df = carregar_csv_licenciamento(arquivo_csv)

    if arquivo_correcoes is not None:
        df_correcoes = pd.read_csv(arquivo_correcoes)
        df = aplicar_correcoes_coordenadas(df, df_correcoes)

    df_alvo = pd.read_csv(arquivo_alvo) if arquivo_alvo is not None else None
    df_nao_alvo = pd.read_csv(arquivo_nao_alvo) if arquivo_nao_alvo is not None else None

    st.write(f"**{len(df)}** registros de estação carregados.")

    mapa = construir_mapa(
        df,
        raio_metros=raio_metros,
        predios_alvo=df_alvo,
        predios_nao_alvo=df_nao_alvo,
        usar_satelite=usar_satelite,
    )

    components.html(mapa.get_root().render(), height=750, scrolling=True)

    st.download_button(
        "Baixar mapa como HTML",
        data=mapa.get_root().render(),
        file_name="mapa_erbs.html",
        mime="text/html",
    )

except Exception as erro:
    st.error(f"Erro ao processar os dados: {erro}")

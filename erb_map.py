"""Lógica de geração do mapa de ERBs com setores de azimute.

Adaptado do script original de análise (Google Colab) para uso em Streamlit:
sem dependência de google.colab/tqdm.notebook, com dados de entrada via upload
em vez de caminhos fixos de arquivo.
"""
import math

import folium
import numpy as np
import pandas as pd
from branca.element import Element

COLUNAS_NUMERICAS = ["Latitude", "Longitude", "Azimute", "AnguloMeiaPotenciaAntena"]

TILES_SATELITE = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"


def calcular_destino(lat, lon, azimute, distancia=100):
    """Retorna o ponto (lat, lon) a `distancia` metros de (lat, lon) na direção `azimute`."""
    raio_terra = 6371000
    brng = math.radians(azimute)
    lat1, lon1 = math.radians(lat), math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(distancia / raio_terra)
        + math.cos(lat1) * math.sin(distancia / raio_terra) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(distancia / raio_terra) * math.cos(lat1),
        math.cos(distancia / raio_terra) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def gerar_setor(lat, lon, azimute, abertura, raio=100):
    """Gera o polígono (lista de coordenadas) do setor de cobertura da antena."""
    coords = [[lat, lon]]
    for ang in np.linspace(azimute - abertura / 2, azimute + abertura / 2, 12):
        coords.append(list(calcular_destino(lat, lon, ang, raio)))
    coords.append([lat, lon])
    return coords


def carregar_csv_licenciamento(arquivo):
    """Lê o CSV de licenciamento ANATEL (separador '|') e normaliza as colunas numéricas."""
    df = pd.read_csv(arquivo, sep="|")
    for col in COLUNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"])
    return df


def aplicar_correcoes_coordenadas(df, df_correcoes):
    """Sobrescreve Latitude/Longitude de estações específicas (coluna NumEstacao)."""
    df = df.copy()
    for _, row in df_correcoes.iterrows():
        mask = df["NumEstacao"] == row["NumEstacao"]
        df.loc[mask, "Latitude"] = row["Latitude"]
        df.loc[mask, "Longitude"] = row["Longitude"]
    return df


def _ler_pontos(df_pontos):
    """Extrai lista de (lat, lon) de um DataFrame aceitando colunas Latitude/Longitude ou lat/lon."""
    cols = {c.lower(): c for c in df_pontos.columns}
    col_lat = cols.get("latitude") or cols.get("lat")
    col_lon = cols.get("longitude") or cols.get("lon") or cols.get("lng")
    if not col_lat or not col_lon:
        raise ValueError("O arquivo de prédios precisa ter colunas de latitude e longitude.")
    pontos = df_pontos[[col_lat, col_lon]].apply(pd.to_numeric, errors="coerce").dropna()
    return list(pontos.itertuples(index=False, name=None))


def construir_mapa(
    df,
    raio_metros=100,
    predios_alvo=None,
    predios_nao_alvo=None,
    usar_satelite=True,
):
    """Monta o folium.Map com estações, setores de azimute e marcadores de prédios.

    Parameters
    ----------
    df : DataFrame já filtrado/normalizado (Latitude, Longitude, Azimute, AnguloMeiaPotenciaAntena).
    predios_alvo, predios_nao_alvo : DataFrame opcionais com lat/lon dos prédios de referência.
    """
    df_valido = df.dropna(subset=["Latitude", "Longitude"])
    if df_valido.empty:
        raise ValueError("Nenhuma estação com coordenadas válidas para exibir.")

    if usar_satelite:
        mapa = folium.Map(
            location=[df_valido["Latitude"].mean(), df_valido["Longitude"].mean()],
            zoom_start=15,
            tiles=TILES_SATELITE,
            attr="Google Hybrid",
        )
    else:
        mapa = folium.Map(
            location=[df_valido["Latitude"].mean(), df_valido["Longitude"].mean()],
            zoom_start=15,
        )

    camada_geometrias = folium.FeatureGroup(name="Setores e Azimutes").add_to(mapa)
    camada_estacoes = folium.FeatureGroup(name="Marcadores").add_to(mapa)

    tem_hpbw = "AnguloMeiaPotenciaAntena" in df_valido.columns
    tem_azimute = "Azimute" in df_valido.columns

    if tem_azimute and tem_hpbw:
        df_setores = df_valido.sort_values(
            by=["Latitude", "Longitude", "Azimute", "AnguloMeiaPotenciaAntena"]
        )
        df_setores = df_setores[df_setores["AnguloMeiaPotenciaAntena"] > 0].drop_duplicates(
            subset=["Latitude", "Longitude", "Azimute"], keep="first"
        )

        for row in df_setores.itertuples():
            lat, lon, az, hpbw = row.Latitude, row.Longitude, row.Azimute, row.AnguloMeiaPotenciaAntena
            if math.isnan(az):
                continue

            folium.Circle(
                location=[lat, lon],
                radius=raio_metros,
                color="yellow",
                fill=False,
                weight=3,
                opacity=0.8,
                className="setor-geometria",
            ).add_to(camada_geometrias)

            folium.Polygon(
                locations=gerar_setor(lat, lon, az, hpbw, raio=raio_metros),
                color="yellow",
                fill=True,
                fill_color="yellow",
                fill_opacity=0.2,
                weight=0.5,
                className="setor-geometria",
            ).add_to(camada_geometrias)

            p2 = calcular_destino(lat, lon, az, distancia=raio_metros)
            folium.PolyLine(
                [[lat, lon], p2], color="red", weight=2, className="linha-azimute"
            ).add_to(camada_geometrias)

    colunas_popup = ["NomeEntidade", "Tecnologia", "Municipio.NomeMunicipio", "EnderecoEstacao", "Azimute"]
    df_unique = df_valido.drop_duplicates(subset=["NumEstacao"]) if "NumEstacao" in df_valido.columns else df_valido

    for _, row in df_unique.iterrows():
        popup_linhas = []
        for col in colunas_popup:
            if col in df_unique.columns:
                valor = row[col]
                if pd.notna(valor):
                    popup_linhas.append(f"{col}: {valor}")
        popup_texto = "<br>".join(popup_linhas) if popup_linhas else "Estação"

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=4,
            color="blue",
            fill=True,
            fill_opacity=1,
            popup=folium.Popup(popup_texto, max_width=300),
            className="marcador-ponto",
        ).add_to(camada_estacoes)

    if predios_alvo is not None:
        for lat_alvo, lon_alvo in _ler_pontos(predios_alvo):
            folium.CircleMarker(
                location=[lat_alvo, lon_alvo],
                radius=4,
                color="red",
                fill=True,
                fill_opacity=1,
                popup=f"<b>Prédio Alvo</b><br>{lat_alvo}, {lon_alvo}",
                className="marcador-ponto",
            ).add_to(camada_estacoes)

    if predios_nao_alvo is not None:
        for lat_na, lon_na in _ler_pontos(predios_nao_alvo):
            folium.CircleMarker(
                location=[lat_na, lon_na],
                radius=4,
                color="green",
                fill=True,
                fill_opacity=1,
                popup=f"<b>Prédio Não-Alvo</b><br>{lat_na}, {lon_na}",
                className="marcador-ponto",
            ).add_to(camada_estacoes)

    painel_html = """
    <div id='control-panel' style='position: fixed; bottom: 30px; left: 10px; z-index: 9999;
        background: white; padding: 15px; border: 2px solid #555; border-radius: 10px;
        font-family: Arial; font-size: 12px; box-shadow: 2px 2px 10px rgba(0,0,0,0.3);'>
        <b style='font-size: 14px;'>Controle de Transparência</b><hr>

        <label>Opacidade Mapa Base:</label><br>
        <input id='map-slider' type='range' min='0' max='100' value='100' style='width: 180px;'><br>

        <label>Opacidade Marcadores (Pontos):</label><br>
        <input id='marker-slider' type='range' min='0' max='100' value='100' style='width: 180px;'><br>

        <label>Opacidade Ângulo (Setores/Raios):</label><br>
        <input id='geo-slider' type='range' min='0' max='100' value='100' style='width: 180px;'>
    </div>
    <script>
        setTimeout(function() {
            var mapSlider = document.getElementById('map-slider');
            var markerSlider = document.getElementById('marker-slider');
            var geoSlider = document.getElementById('geo-slider');

            mapSlider.oninput = function() {
                var val = this.value / 100;
                var panes = document.getElementsByClassName('leaflet-tile-pane');
                if (panes.length > 0) panes[0].style.opacity = val;
            };

            markerSlider.oninput = function() {
                var val = this.value / 100;
                document.querySelectorAll('.marcador-ponto').forEach(function(el) {
                    el.style.opacity = val;
                    el.style.fillOpacity = val;
                });
            };

            geoSlider.oninput = function() {
                var val = this.value / 100;
                document.querySelectorAll('.setor-geometria, .linha-azimute').forEach(function(el) {
                    el.style.opacity = val;
                    if (el.classList.contains('setor-geometria') && el.tagName === 'path' && el.getAttribute('fill') !== 'none') {
                        el.style.fillOpacity = val * 0.2;
                    } else {
                        el.style.fillOpacity = val;
                    }
                });
            };
        }, 1000);
    </script>
    """
    mapa.get_root().html.add_child(Element(painel_html))
    folium.LayerControl().add_to(mapa)
    return mapa

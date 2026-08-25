# 🌊 Mapeamento Interativo de Alagamentos e Macro-Zonas de São Paulo

> **Visualização geoespacial interativa combinando mapa de calor de eventos históricos de alagamento/inundação com os limites territoriais das 5 Macro-Zonas da cidade de São Paulo.**

🔗 **[Clique aqui para acessar o Mapa Interativo Online](https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/)**

---

## 📌 Visão Geral do Projeto

Este projeto realiza a ingestão, tratamento e integração de dados geoespaciais abertos da cidade de São Paulo para analisar a distribuição espacial de ocorrências de alagamentos e inundações. 

A solução sobrepõe duas camadas cruciais em um mapa web interativo (Folium/Leaflet):
1. **Mapa de Calor (HeatMap):** Densidade espacial dos eventos de alagamento registrados.
2. **Camada Vetorial (Macro-Zonas):** Agrupamento administrativo das 32 subprefeituras de São Paulo em 5 regiões territoriais (Centro, Norte, Leste, Oeste e Sul).

![Demonstração do Mapa](https://raw.githubusercontent.com/SEU-USUARIO/NOME-DO-REPOSITORIO/main/imagem_mapa.png) <!-- Adicione uma print do mapa aqui -->

---

## 🛠️ Desafios Técnicos & Engenharia de Dados

Durante o desenvolvimento do pipeline de dados, foram aplicadas as seguintes técnicas geoespaciais:

* **Reprojeção do Sistema de Coordenadas (CRS):**
  * Os dados brutos de alagamentos estavam projetados em **UTM SIRGAS 2000 (EPSG:31983)** em metros.
  * Foi realizada a conversão reprojetando para **WGS84 (EPSG:4326)** em graus decimais, garantindo a renderização precisa das coordenadas no Folium/Leaflet.

* **Agregação Territorial (Dissolve & Mapping):**
  * Cruzamento e limpeza da tabela de atributos do Shapefile oficial do GeoSampa (`nm_subpref`).
  * Agrupamento espacial (`.dissolve()`) das 32 subprefeituras originais nas 5 Macro-Zonas municipais.

* **Otimização Geoespacial (Emagrecimento de Dados):**
  * Aplicação do algoritmo de simplificação de polígonos (`.simplify(tolerance=0.001)`) para reduzir o número de vértices sem perder a precisão visual do contorno.
  * Filtro e eliminação de colunas administrativas pesadas e incompatíveis (como *Timestamps*), exportando um arquivo GeoJSON enxuto de alta performance para a web.

---

## 🧰 Tecnologias Utilizadas

* **Linguagem:** Python 3.13
* **Análise de Dados & GIS:** `pandas`, `geopandas`, `shapely`, `pyproj`
* **Visualização Interativa:** `folium` (Plugin `HeatMap`, `GeoJson`, `LayerControl`)
* **Hospedagem Web:** GitHub Pages

---

## 📁 Estrutura do Repositório

```text
├── data/
│   ├── alagamentos_e_inundacoes_sp.csv   # Dataset de eventos históricos
│   └── macro_zonas_sp_otimizado.geojson  # Limites territoriais simplificados
├── notebooks/
│   └── mapa_alagamentos_sp.ipynb         # Notebook completo do processamento ETL
├── index.html                            # Aplicação web final gerada pelo Folium
└── README.md                             # Documentação do projeto

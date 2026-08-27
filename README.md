# 🌊 Mapeamento Interativo de Alagamentos e Macro-Zonas de São Paulo

> **Visualização geoespacial interativa combinando mapa de calor de eventos históricos de alagamento com os limites territoriais das 5 Macro-Zonas da cidade de São Paulo.**

🌐 **[Acessar o Mapa Interativo Online (GitHub Pages)](https://23216886alunounivesp.github.io/mapa-alagamentos-sp/)**

---

## 🗺️ Visualizações Interativas Disponíveis

Este repositório disponibiliza diferentes saídas cartográficas geradas pelo pipeline:
* **[mapa.html](mapa.html):** Versão padrão do mapa interativo contendo o mapa de calor e as camadas geográficas principais.
* **[mapa_zonas_interativo.html](mapa_zonas_interativo.html):** **Versão avançada e interativa** focada na exploração detalhada das 5 Macro-Zonas e sua sobreposição com os alagamentos.

---

## 📌 Visão Geral do Projeto

Este projeto realiza a ingestão, tratamento e integração de dados geoespaciais abertos da cidade de São Paulo para analisar a distribuição espacial de ocorrências de alagamentos e inundações.

A aplicação web sobrepõe duas camadas em um mapa interativo desenvolvido em Python (Folium/Leaflet):

1. **Mapa de Calor (HeatMap):** Densidade espacial e concentração histórica dos registros de alagamento.
2. **Camada Vetorial (Macro-Zonas):** Limites territoriais municipais gerados a partir do agrupamento das 32 subprefeituras em 5 regiões (Centro, Norte, Leste, Oeste e Sul).

---

## 🛠️ Engenharia de Dados & Desafios Geoespaciais

Durante o desenvolvimento do pipeline de dados (ETL), foram resolvidas as seguintes etapas técnicas:

* **Reprojeção do Sistema de Coordenadas (CRS):**
  * Os dados brutos de alagamentos estavam projetados em **UTM SIRGAS 2000 (EPSG:31983)** em metros.
  * Foi realizada a conversão vetorial reprojetando as coordenadas para **WGS84 (EPSG:4326)** em graus decimais, garantindo o alinhamento no Folium/Leaflet.

* **Agregação Territorial (Dissolve & Mapping):**
  * Limpeza da tabela de atributos do Shapefile oficial das subprefeituras (`nm_subpref`).
  * Agrupamento espacial (`.dissolve()`) das 32 subprefeituras originais nas 5 Macro-Zonas municipais.

* **Otimização Geoespacial (Emagrecimento de Dados):**
  * Aplicação do algoritmo de simplificação de polígonos (`.simplify(tolerance=0.001)`) para reduzir o número de vértices sem comprometer a precisão visual do contorno.
  * Remoção de colunas administrativas e tipos não serializáveis (*Timestamps*), gerando um arquivo `.geojson` enxuto e de alta performance para carregamento web instantâneo.

---

## 🧰 Tecnologias Utilizadas

* **Linguagem:** Python 3.13
* **Análise de Dados & GIS:** `pandas`, `geopandas`, `shapely`, `pyproj`
* **Visualização Interativa:** `folium` (Plugins `HeatMap`, `GeoJson`, `LayerControl`)
* **Hospedagem Web:** GitHub Pages

---

## 📁 Estrutura do Repositório

```text
.
├── data/
│   ├── alagamentos_e_inundacoes_sp.csv     # Dataset de eventos históricos (UTM)
│   └── macro_zonas_sp_otimizado.geojson    # GeoJSON otimizado das 5 Macro-Zonas
├── notebooks/
│   └── mapa_alagamentos_sp.ipynb           # Notebook completo do tratamento e geração
├── mapa.html                               # Mapa interativo básico gerado pelo Folium
├── mapa_zonas_interativo.html              # Mapa interativo avançado focado nas Macro-Zonas
├── index.html                              # Nova página principal (Documentação + iframe)
└── README.md                               # Documentação do repositório

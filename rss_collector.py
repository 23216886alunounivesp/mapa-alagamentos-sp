import os
import time
import feedparser
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceCreated

# Configurações do Supabase obtidas das Variáveis de Ambiente (Secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ebknsiiirqpfsrjewpou.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_KU-HNUH_WR3uagFDzubHvQ_AvACKYVO")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# Lista de Feeds RSS para monitoramento
FEEDS_RSS = [
    {"nome": "G1 São Paulo", "url": "https://g1.globo.com/rss/g1/sao-paulo/"},
    {"nome": "R7 São Paulo", "url": "https://noticias.r7.com/sao-paulo/feed.xml"}
]

PALAVRAS_CHAVE = [
    "alagamento", "alagados", "alagada", "enxurrada", 
    "transbordo", "transbordou", "chuva forte", "pista alagada"
]

geolocator = Nominatim(user_agent="sp_alagamentos_univesp_bot")

def extrair_bairro_ou_local(texto):
    texto_lower = texto.lower()
    bairros_sp = [
        "mooca", "tatuapé", "ipiranga", "itaim paulista", "vila mariana",
        "pinheiros", "santana", "santo amaro", "aricanduva", "butantã",
        "lapa", "campo limpo", "jabaquara", "são miguel", "pirituba",
        "marginal tietê", "marginal pinheiros", "avenida paulista",
        "avenida anhaia mello", "radial leste"
    ]
    for bairro in bairros_sp:
        if bairro in texto_lower:
            return bairro.title()
    return "São Paulo"

def geocodificar_endereco(local_texto):
    try:
        busca = f"{local_texto}, São Paulo, SP, Brasil"
        location = geolocator.geocode(busca, timeout=10)
        if location and -24.1 <= location.latitude <= -23.3 and -46.9 <= location.longitude <= -46.3:
            return location.latitude, location.longitude
    except (GeocoderTimedOut, GeocoderServiceCreated) as e:
        print(f"⚠️ Timeout na geocodificação: {e}")
    return -23.55052, -46.63330

def salvar_noticia_supabase(titulo, veiculo, link, bairro, lat, lon):
    payload = {
        "titulo": titulo,
        "veiculo_imprensa": veiculo,
        "link_noticia": link,
        "bairro": bairro,
        "latitude": lat,
        "longitude": lon,
        "aprovado": False,
        "status_moderacao": "pendente"
    }
    
    endpoint = f"{SUPABASE_URL}/rest/v1/noticias_rss"
    response = requests.post(endpoint, json=payload, headers=HEADERS)
    
    if response.status_code in [200, 201]:
        print(f"✅ Notícia registrada: {titulo[:40]}... ({bairro})")
    else:
        print(f"❌ Erro ao gravar no Supabase: {response.text}")

def executar_coleta_rss():
    print("🚀 Iniciando varredura automatizada de feeds RSS...")
    total_encontradas = 0

    for feed in FEEDS_RSS:
        print(f"📡 Lendo feed: {feed['nome']}...")
        parsed_feed = feedparser.parse(feed['url'])
        
        for entry in parsed_feed.entries:
            titulo = entry.get('title', '')
            resumo = entry.get('summary', '')
            link = entry.get('link', '')
            
            conteudo_completo = f"{titulo} {resumo}".lower()
            
            if any(palavra in conteudo_completo for palavra in PALAVRAS_CHAVE):
                bairro_extraido = extrair_bairro_ou_local(conteudo_completo)
                lat, lon = geocodificar_endereco(bairro_extraido)
                
                salvar_noticia_supabase(
                    titulo=titulo,
                    veiculo=feed['nome'],
                    link=link,
                    bairro=bairro_extraido,
                    lat=lat,
                    lon=lon
                )
                total_encontradas += 1
                time.sleep(1)

    print(f"✨ Coleta concluída! {total_encontradas} matérias enviadas para moderação.")

if __name__ == "__main__":
    executar_coleta_rss()

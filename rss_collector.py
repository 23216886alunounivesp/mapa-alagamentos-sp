import os
import re
import time
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import quote
import feedparser
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError

# ==============================================================================
# CONFIGURAÇÕES E CREDENCIAIS DO SUPABASE
# ==============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ebknsiiirqpfsrjewpou.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_KU-HNUH_WR3uagFDzubHvQ_AvACKYVO")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Parâmetros do Filtro e Trava Temporal
SCORE_MINIMO = 4           # Pontuação mínima de relevância (Conteúdo + Geografia)
JANELA_HORAS_LOCAL = 24    # Janela em horas para impedir duplicatas do mesmo local

# ==============================================================================
# 1. NORMALIZAÇÃO DE TEXTO
# ==============================================================================
def normalizar(t):
    if not t:
        return ""
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")

# ==============================================================================
# 2. CLASSIFICAÇÃO E PONTUAÇÃO DE CONTEÚDO (EVENTOS HÍDRICOS)
# ==============================================================================
CATEGORIAS_EVENTO = {
    "evento": [ # Peso 5
        "alagamento", "alagamentos", "alagado", "alagada", "alagados", "alagou",
        "enxurrada", "enchente", "enchentes", "inundacao", "inundacoes", "inundou",
        "transbordou", "transbordo", "transbordamento", "extravasou",
        "bolsao de agua", "bolsoes de agua", "ponto de alagamento",
        "pista alagada", "via alagada", "rua alagada", "avenida alagada",
        "tunel alagado", "passagem alagada", "underpass alagado",
        "agua ate a cintura", "carros ilhados", "carro arrastado", "ilhados"
    ],
    "alerta": [ # Peso 4
        "estado de atencao", "estado de alerta", "estado de emergencia",
        "alerta de chuva", "alerta de tempestade", "aviso de tempestade",
        "alerta severo", "perigo potencial", "perigo", "alerta laranja",
        "alerta vermelho", "alerta amarelo", "defesa civil", "cge",
        "risco de alagamento", "risco de inundacao", "risco de deslizamento"
    ],
    "hidro": [ # Peso 2
        "rio tiete", "rio pinheiros", "rio tamanduatei", "rio aricanduva",
        "rio embu-guacu", "rio juqueri", "corrego", "corregos", "ribeirao",
        "nivel do rio", "cota de inundacao", "cheia", "vazao",
        "piscinao", "piscinoes", "reservatorio", "represa billings",
        "billings", "guarapiranga", "cantareira", "sistema cantareira",
        "comporta", "bueiro entupido", "drenagem", "boca de lobo"
    ],
    "clima": [ # Peso 2
        "chuva forte", "chuvas fortes", "chuva intensa", "temporal", "temporais",
        "tempestade", "pancadas de chuva", "chuva de granizo", "granizo",
        "ventania", "rajadas de vento", "frente fria", "zcas", "acumulado de chuva"
    ],
    "impacto": [ # Peso 2
        "pista bloqueada", "via interditada", "interdicao", "interditada",
        "lentidao", "transito parado", "congestionamento", "marginal tiete",
        "marginal pinheiros", "marginal alagada", "queda de arvore",
        "deslizamento", "desabamento", "desmoronamento", "queda de energia",
        "metro paralisado", "estacao fechada", "linha paralisada", "cptm"
    ]
}

EXCLUIR = [
    "inundacao de ofertas", "enxurrada de criticas", "enxurrada de pedidos",
    "enxurrada de denuncias", "enxurrada de memes", "enchente de gols",
    "alagamento de mercado", "inundacao de conteudo", "chuva de gols",
    "chuva de elogios", "chuva de criticas", "chuva de premios",
    "chuva de ouro", "transbordou de alegria"
]

def avaliar_relevancia_evento(texto):
    t = normalizar(texto)
    if any(normalizar(x) in t for x in EXCLUIR):
        return 0

    pesos = {"evento": 5, "alerta": 4, "hidro": 2, "clima": 2, "impacto": 2}
    score = 0
    for cat, termos in CATEGORIAS_EVENTO.items():
        for termo in termos:
            if re.search(rf"\b{re.escape(termo)}\b", t):
                score += pesos[cat]
    return score

# ==============================================================================
# 3. LOCAIS CRÍTICOS PONDERADOS DE SÃO PAULO
# ==============================================================================
LOCAIS_SP = {
    "rios_corregos": {
        "peso": 3,
        "termos": [
            "rio tiete", "rio pinheiros", "rio tamanduatei", "rio aricanduva",
            "rio jaguare", "rio cabuçu de baixo", "rio cabucu de baixo",
            "rio embu-mirim", "rio guaió", "rio guaio", "rio jurubatuba",
            "rio verde", "rio eliseu de almeida", "rio itaim",
            "corrego aguas espraiada", "corrego agua espraiada",
            "corrego do ipiranga", "corrego ipiranga", "corrego pirajussara",
            "corrego zavuvus", "corrego uberaba", "corrego cordeiro",
            "corrego verde", "corrego mooca", "corrego tiquatira",
            "corrego agua preta", "corrego anhangabau", "corrego saracura",
            "corrego do sapateiro", "corrego sapateiro", "corrego guamiranga",
            "corrego ponte baixa", "corrego morro do s", "corrego itaim",
            "corrego pirituba", "corrego agua podre", "corrego do limoeiro",
            "corrego limoeiro", "corrego do bananal", "corrego bananal",
            "corrego pocinho", "corrego do rincao", "corrego rincao",
            "corrego vila guilherme", "corrego carandiru", "corrego mandaqui",
            "corrego bem-te-vi", "corrego do cassandoca", "corrego cassandoca",
            "corrego do oratorio", "corrego oratorio", "corrego moinho velho",
            "corrego da traicao", "corrego traicao", "corrego jaguare",
            "ribeirao dos meninos", "ribeirao vermelho", "ribeirao perus",
            "ribeirao caulim", "ribeirao pirituba"
        ],
    },
    "piscinoes": {
        "peso": 3,
        "termos": [
            "piscinao do pacaembu", "piscinao pacaembu", "piscinao do pinheirinho",
            "piscinao pinheirinho", "piscinao aricanduva", "piscinao do aricanduva",
            "piscinao guamiranga", "piscinao do sapateiro", "piscinao sapateiro",
            "piscinao pirajussara", "piscinao do pirajussara", "piscinao anhanguera",
            "piscinao eliseu de almeida", "piscinao do rincao", "piscinao rincao",
            "piscinao da traicao", "piscinao traicao", "piscinao uberaba",
            "piscinao do limoeiro", "piscinao limoeiro", "piscinao bananal",
            "piscinao sao mateus", "piscinao do mandaqui", "piscinao mandaqui",
            "piscinao do cassandoca", "piscinao tremembe", "piscinao do carandiru",
            "piscinao inhumas", "piscinao do jabaquara", "piscinao jabaquara",
            "piscinao praça da bandeira", "piscinao pirituba", "piscinao freguesia",
            "piscinao da vila prudente", "piscinao oratorio", "piscinao guaraciaba",
            "reservatorio de detencao", "reservatorio de contencao",
            "reservatorio aricanduva", "bacia de detencao"
        ],
    },
    "avenidas_expressas": {
        "peso": 3,
        "termos": [
            "marginal tiete", "marginal pinheiros", "marginais", "marginal alagada",
            "avenida do estado", "av. do estado", "av do estado",
            "avenida tiradentes", "av. tiradentes", "avenida dos bandeirantes",
            "av. dos bandeirantes", "avenida 23 de maio", "av. 23 de maio",
            "avenida nove de julho", "av. nove de julho", "av. 9 de julho",
            "avenida 9 de julho", "avenida radial leste", "radial leste",
            "avenida jacu pessego", "avenida jacu-pessego", "av. jacu-pessego",
            "avenida aricanduva", "av. aricanduva", "avenida roberto marinho",
            "av. roberto marinho", "avenida washington luis", "av. washington luis",
            "avenida ibirapuera", "av. ibirapuera", "avenida cruzeiro do sul",
            "av. cruzeiro do sul", "avenida inajar de souza", "av. inajar de souza",
            "avenida santo amaro", "av. santo amaro", "avenida morumbi",
            "av. morumbi", "avenida giovanni gronchi", "av. giovanni gronchi",
            "avenida interlagos", "av. interlagos", "avenida cupece", "av. cupece",
            "avenida joao dias", "av. joao dias", "avenida eusebio matoso",
            "avenida rebouças", "avenida reboucas", "av. reboucas",
            "avenida faria lima", "av. faria lima", "avenida brasil",
            "avenida paulista", "avenida rio branco", "avenida ipiranga",
            "avenida celso garcia", "av. celso garcia", "avenida salim farah maluf",
            "avenida sapopemba", "av. sapopemba", "avenida mateo bei",
            "avenida professor luiz ignacio anhaia mello", "av. anhaia mello",
            "avenida do cursino", "avenida lins de vasconcelos",
            "avenida dr. ricardo jafet", "avenida ricardo jafet",
            "avenida bosque da saude", "avenida jabaquara", "av. jabaquara",
            "avenida pedroso de moraes", "avenida sumare", "avenida pompeia",
            "avenida marques de sao vicente", "avenida francisco matarazzo",
            "avenida casa verde", "avenida otaviano alves de lima",
            "avenida inajar", "avenida mutinga", "avenida raimundo pereira de magalhaes",
            "avenida deputado emilio carlos", "avenida edgar facó", "avenida edgar faco",
            "avenida marechal tito", "avenida itaquera", "avenida conceicao",
            "avenida zaki narchi", "avenida eng. caetano alvares",
            "avenida engenheiro caetano alvares", "avenida leao xiii",
            "avenida santos dumont", "avenida cangaiba", "avenida nordestina",
            "avenida boturussu", "avenida sao miguel", "avenida padre arlindo vieira",
            "avenida ragueb chohfi", "avenida teotonio vilela", "avenida atlantica",
            "avenida guarapiranga", "avenida robert kennedy", "avenida joao pessoa"
        ],
    },
    "rodovias_acessos": {
        "peso": 2,
        "termos": [
            "rodoanel", "rodoanel mario covas", "rodovia dos imigrantes", "imigrantes",
            "via anchieta", "anchieta", "rodovia castelo branco", "castelo branco",
            "rodovia raposo tavares", "raposo tavares", "rodovia regis bittencourt",
            "regis bittencourt", "rodovia fernao dias", "fernao dias",
            "via dutra", "dutra", "rodovia presidente dutra", "rodovia ayrton senna",
            "ayrton senna", "rodovia dos trabalhadores", "rodovia anhanguera",
            "anhanguera", "rodovia dos bandeirantes", "rodovia bandeirantes",
            "rodovia carvalho pinto", "rodovia ermelino matarazzo",
            "estrada de itapecerica", "estrada do m'boi mirim", "estrada do mboi mirim",
            "estrada de parelheiros", "estrada do campo limpo", "estrada de santa catarina",
            "estrada do embu", "estrada do jaguare", "estrada de sao miguel",
            "estrada do alvarenga", "estrada do barro branco", "complexo viario",
            "alca de acesso", "trevo"
        ],
    },
    "pontes_tuneis": {
        "peso": 3,
        "termos": [
            "ponte das bandeiras", "ponte do limao", "ponte da casa verde",
            "ponte cruzeiro do sul", "ponte do piqueri", "ponte julio de mesquita neto",
            "ponte do tatuape", "ponte ayrton senna", "ponte jaguare", "ponte cidade jardim",
            "ponte eusebio matoso", "ponte octavio frias de oliveira", "ponte estaiada",
            "ponte laguna", "ponte do socorro", "ponte do morumbi", "ponte morumbi",
            "ponte engenheiro ary torres", "ponte livre", "ponte vila guilherme",
            "ponte da freguesia do o", "ponte freguesia do o", "ponte do cebolao",
            "ponte dos remedios", "ponte remedios", "ponte joao dias",
            "viaduto do cha", "viaduto santa efigenia", "viaduto major quedinho",
            "viaduto antartica", "viaduto bresser", "viaduto tiradentes",
            "viaduto bras leme", "viaduto cidade de lisboa", "viaduto jaceguai",
            "viaduto dona paulina", "viaduto doutor arnaldo", "viaduto pacaembu",
            "viaduto da avenida do estado", "viaduto do glicerio", "viaduto glicerio",
            "tunel anhangabau", "tunel nove de julho", "tunel 9 de julho",
            "tunel ayrton senna", "tunel jornalista fernando vieira de mello",
            "tunel max feffer", "tunel sebastiao camargo", "tunel tom jobim",
            "tunel daher elias cutait", "tunel jose roberto fantini",
            "tunel da rua vergueiro", "tunel rebouças", "tunel reboucas",
            "tunel da avenida paulista", "tunel do pacaembu", "tunel pacaembu",
            "tunel da avenida faria lima", "tunel da avenida brasil",
            "passagem subterranea", "underpass", "passagem de nivel",
            "tunel", "viaduto", "ponte"
        ],
    },
    "pracas_pontos": {
        "peso": 3,
        "termos": [
            "vale do anhangabau", "anhangabau", "praca da se", "praca da bandeira",
            "largo da batata", "largo treze de maio", "largo 13 de maio",
            "largo do cambuci", "largo sao francisco", "praca roosevelt",
            "praca da republica", "praca do correio", "praca julio mesquita",
            "praca marechal deodoro", "praca princesa isabel",
            "praca panamericana", "praça panamericana", "praca charles miller",
            "cebolao", "complexo do cebolao", "cebolao do tiete", "praca do ciclista",
            "ceagesp", "mercado municipal", "mercadao", "25 de marco",
            "rua 25 de marco", "ladeira porto geral", "bras", "brás",
            "terminal tiete", "rodoviaria do tiete", "terminal barra funda",
            "terminal bandeira", "terminal parque dom pedro", "terminal sacoma",
            "terminal santo amaro", "terminal capelinha", "terminal jabaquara",
            "terminal vila prudente", "terminal itaquera", "terminal sao mateus",
            "terminal grajau", "terminal varginha", "terminal campo limpo",
            "terminal capao redondo", "terminal pinheiros", "terminal lapa",
            "terminal santana", "terminal amaral gurgel", "terminal princesa isabel",
            "terminal sao miguel", "terminal vila nova cachoeirinha",
            "terminal penha", "terminal carrao", "terminal guarapiranga",
            "terminal joao dias", "terminal cidade tiradentes",
            "estadio do pacaembu", "pacaembu", "allianz parque", "neo quimica arena",
            "arena corinthians", "morumbi", "estadio do morumbi", "parque ibirapuera",
            "parque da agua branca", "parque do carmo", "parque ecologico do tiete",
            "parque linear", "interlagos autodromo", "autodromo de interlagos",
            "aeroporto de congonhas", "congonhas", "campo de marte",
            "sambodromo", "anhembi", "expo center norte", "expo barra funda",
            "shopping aricanduva", "shopping tiete plaza", "shopping eldorado",
            "shopping morumbi", "shopping iguatemi", "shopping center norte",
            "shopping interlagos", "shopping sao paulo", "shopping jardim sul"
        ],
    },
    "ruas_criticas": {
        "peso": 3,
        "termos": [
            "rua 25 de marco", "rua jose bonifacio", "rua florencio de abreu",
            "rua do gasometro", "rua do hipodromo", "rua javari", "rua da mooca",
            "rua bresser", "rua catumbi", "rua piratininga", "rua monsenhor andrade",
            "rua tuiuti", "rua maria marcolina", "rua henrique schaumann",
            "rua teodoro sampaio", "rua cardeal arcoverde", "rua dos pinheiros",
            "rua jose paulino", "rua sao caetano", "rua das olarias",
            "rua do manifesto", "rua do oratorio", "rua dos patriotas",
            "rua silva bueno", "rua tamandare", "rua vergueiro", "rua domingos de morais",
            "rua jose de barros", "rua augusta", "rua consolacao", "rua da consolacao",
            "rua frei caneca", "rua haddock lobo", "rua alves guimaraes",
            "rua doutor arnaldo", "rua cerro cora", "rua pio xi", "rua heitor penteado",
            "rua clelia", "rua joao ramalho", "rua turiassu", "rua barra funda",
            "rua lopes de oliveira", "rua guaicurus", "rua catao", "rua carlos vicari",
            "rua senador queiros", "rua general carneiro", "rua brigadeiro tobias",
            "rua mauá", "rua maua", "rua sao joao", "rua guaianases",
            "rua conselheiro furtado", "rua da gloria", "rua do glicerio",
            "rua lavapes", "rua independencia", "rua do lavapes",
            "rua ipiranga", "rua loefgreen", "rua pedro de toledo"
        ],
    },
    "estacoes": {
        "peso": 2,
        "termos": [
            "estacao se", "estacao republica", "estacao anhangabau",
            "estacao sao bento", "estacao luz", "estacao brás", "estacao bras",
            "estacao tatuape", "estacao carrao", "estacao penha", "estacao armenia",
            "estacao portuguesa-tiete", "estacao portuguesa tiete", "estacao carandiru",
            "estacao santana", "estacao jabaquara", "estacao saude", "estacao conceicao",
            "estacao vila mariana", "estacao paraiso", "estacao ana rosa",
            "estacao brigadeiro", "estacao trianon-masp", "estacao consolacao",
            "estacao clinicas", "estacao sumare", "estacao vila madalena",
            "estacao pinheiros", "estacao butanta", "estacao faria lima",
            "estacao fradique coutinho", "estacao oscar freire", "estacao paulista",
            "estacao tamanduatei", "estacao vila prudente", "estacao sacoma",
            "estacao santo amaro", "estacao largo treze", "estacao socorro",
            "estacao jurubatuba", "estacao autodromo", "estacao interlagos",
            "estacao grajau", "estacao berrini", "estacao morumbi", "estacao vila olimpia",
            "estacao hebraica rebouças", "estacao cidade jardim", "estacao villa-lobos",
            "estacao presidente altino", "estacao osasco", "estacao lapa",
            "estacao barra funda", "estacao palmeiras-barra funda",
            "estacao julio prestes", "estacao jaguare", "estacao pirituba",
            "estacao jaragua", "estacao vila clarice", "estacao corinthians-itaquera",
            "estacao itaquera", "estacao patriarca", "estacao guilhermina-esperanca",
            "estacao vila matilde", "estacao artur alvim", "estacao sao paulo-morumbi",
            "estacao mooca", "estacao ipiranga", "estacao ermelino matarazzo",
            "estacao ceasa", "estacao engenheiro goulart", "estacao calmon viana",
            "estacao dom bosco", "estacao jardim romano", "estacao tiete",
            "estacao pedro ii", "estacao parque dom pedro", "estacao aeroporto-guarulhos",
            "linha 1-azul", "linha 2-verde", "linha 3-vermelha", "linha 4-amarela",
            "linha 5-lilas", "linha 7-rubi", "linha 8-diamante", "linha 9-esmeralda",
            "linha 10-turquesa", "linha 11-coral", "linha 12-safira", "linha 15-prata",
            "monotrilho", "linha azul", "linha verde", "linha vermelha",
            "linha amarela", "linha lilas", "linha rubi", "linha diamante",
            "linha esmeralda", "linha turquesa", "linha coral", "linha safira", "linha prata"
        ],
    },
    "subprefeituras": {
        "peso": 2,
        "termos": [
            "subprefeitura aricanduva", "subprefeitura butanta", "subprefeitura campo limpo",
            "subprefeitura capela do socorro", "subprefeitura casa verde",
            "subprefeitura cidade ademar", "subprefeitura cidade tiradentes",
            "subprefeitura ermelino matarazzo", "subprefeitura freguesia",
            "subprefeitura guaianases", "subprefeitura ipiranga", "subprefeitura itaim paulista",
            "subprefeitura itaquera", "subprefeitura jabaquara", "subprefeitura jacana",
            "subprefeitura lapa", "subprefeitura m'boi mirim", "subprefeitura mboi mirim",
            "subprefeitura mooca", "subprefeitura parelheiros", "subprefeitura penha",
            "subprefeitura perus", "subprefeitura pinheiros", "subprefeitura pirituba",
            "subprefeitura santana", "subprefeitura santo amaro", "subprefeitura sao mateus",
            "subprefeitura sao miguel", "subprefeitura se", "subprefeitura sapopemba",
            "subprefeitura vila maria", "subprefeitura vila mariana", "subprefeitura vila prudente"
        ],
    },
    "regioes": {
        "peso": 1,
        "termos": [
            "zona leste", "zona sul", "zona norte", "zona oeste", "centro de sao paulo",
            "centro de sp", "regiao central", "extremo sul", "extremo leste",
            "extremo norte", "zona centro-oeste", "zona central"
        ],
    },
}

BAIRROS_POR_SUBPREFEITURA = {
    "se": ["se", "bras", "bom retiro", "bela vista", "cambuci", "consolacao", "liberdade", "republica", "santa cecilia", "pari", "belem"],
    "mooca": ["mooca", "agua rasa", "belem", "brás", "tatuape", "belenzinho"],
    "aricanduva": ["aricanduva", "vila formosa", "carrao"],
    "penha": ["penha", "cangaiba", "artur alvim", "vila matilde", "penha de franca"],
    "ermelino matarazzo": ["ermelino matarazzo", "ponte rasa"],
    "sao miguel": ["sao miguel paulista", "jardim helena", "vila jacui"],
    "itaim paulista": ["itaim paulista", "vila curuca", "jardim romano"],
    "guaianases": ["guaianases", "lajeado"],
    "cidade tiradentes": ["cidade tiradentes"],
    "itaquera": ["itaquera", "cidade lider", "jose bonifacio", "parque do carmo"],
    "sao mateus": ["sao mateus", "sao rafael", "iguatemi", "vila renato"],
    "sapopemba": ["sapopemba"],
    "vila prudente": ["vila prudente", "sao lucas"],
    "ipiranga": ["ipiranga", "sacoma", "cursino", "vila independencia"],
    "vila mariana": ["vila mariana", "saude", "moema", "jabaquara"],
    "jabaquara": ["jabaquara"],
    "santo amaro": ["santo amaro", "campo belo", "campo grande", "brooklin"],
    "cidade ademar": ["cidade ademar", "pedreira"],
    "capela do socorro": ["socorro", "cidade dutra", "grajau", "interlagos"],
    "parelheiros": ["parelheiros", "marsilac"],
    "campo limpo": ["campo limpo", "capao redondo", "vila andrade"],
    "mboi mirim": ["jardim angela", "jardim sao luis", "m'boi mirim"],
    "butanta": ["butanta", "morumbi", "raposo tavares", "rio pequeno", "vila sonia"],
    "pinheiros": ["pinheiros", "alto de pinheiros", "itaim bibi", "jardim paulista"],
    "lapa": ["lapa", "barra funda", "agua branca", "perdizes", "vila leopoldina", "jaguare"],
    "freguesia": ["freguesia do o", "brasilandia"],
    "casa verde": ["casa verde", "cachoeirinha", "limao"],
    "pirituba": ["pirituba", "jaragua", "sao domingos"],
    "perus": ["perus", "anhanguera"],
    "santana": ["santana", "tucuruvi", "mandaqui", "tremembe", "vila guilherme"],
    "jacana": ["jacana", "tremembe"],
    "vila maria": ["vila maria", "vila guilherme", "vila medeiros"],
}

GENERICOS = {
    "ponte", "tunel", "viaduto", "bras", "morumbi", "anchieta",
    "imigrantes", "dutra", "trevo", "marginais", "avenida brasil"
}

def _compilar_padroes():
    padroes = []
    for cat, cfg in LOCAIS_SP.items():
        for termo in set(cfg["termos"]):
            n = normalizar(termo)
            padroes.append((cat, termo, cfg["peso"], re.compile(rf"\b{re.escape(n)}\b")))
    padroes.sort(key=lambda x: -len(x[1])) # Prioriza expressões mais longas
    return padroes

PADROES_GEOGRAFICOS = _compilar_padroes()

def extrair_locais(texto):
    t = normalizar(texto)
    achados, ocupado = [], []
    for cat, termo, peso, rx in PADROES_GEOGRAFICOS:
        for m in rx.finditer(t):
            if any(m.start() < e and m.end() > s for s, e in ocupado):
                continue
            ocupado.append((m.start(), m.end()))
            achados.append({"categoria": cat, "termo": termo, "peso": peso})
    especificos = [a for a in achados if normalizar(a["termo"]) not in GENERICOS]
    return especificos if especificos else []

def pontuar_local(texto):
    return sum(a["peso"] for a in extrair_locais(texto))

def subprefeitura_provavel(texto):
    t = normalizar(texto)
    cont = {}
    for sub, bairros in BAIRROS_POR_SUBPREFEITURA.items():
        for b in bairros:
            if re.search(rf"\b{re.escape(normalizar(b))}\b", t):
                cont[sub] = cont.get(sub, 0) + 1
    return max(cont, key=cont.get) if cont else None

# ==============================================================================
# 4. GERADOR DE FEEDS RSS
# ==============================================================================
def obter_lista_completa_feeds():
    feeds = [
        {"nome": "INMET Avisos", "url": "https://apiprevmet3.inmet.gov.br/avisos/rss"},
        {"nome": "Governo SP", "url": "https://www.saopaulo.sp.gov.br/feed/"},
        {"nome": "Prefeitura SP", "url": "https://www.capital.sp.gov.br/feed"},
        {"nome": "Reddit r/saopaulo", "url": "https://www.reddit.com/r/saopaulo/search.rss?q=alagamento+OR+enchente+OR+chuva&restrict_sr=1&sort=new"},
        {"nome": "Mastodon #alagamento", "url": "https://mastodon.social/tags/alagamento.rss"},
        {"nome": "G1 São Paulo", "url": "https://g1.globo.com/rss/g1/sao-paulo/"},
        {"nome": "R7 São Paulo", "url": "https://noticias.r7.com/sao-paulo/feed.xml"},
        {"nome": "CNN Brasil SP", "url": "https://www.cnnbrasil.com.br/tudo-sobre/sao-paulo/feed/"},
        {"nome": "Diário do Grande ABC", "url": "https://www.dgabc.com.br/rss"}
    ]

    consultas_gnews = [
        'alagamento "São Paulo"',
        'transbordou "São Paulo"',
        'CGE "estado de atencao" alagamento',
        'Marginal Tietê OR Pinheiros alagada',
        'rio Tietê transbordou OR "nível do rio"',
        'piscinao cheio OR transbordou "São Paulo"'
    ]

    for q in consultas_gnews:
        q_encoded = quote(f'{q} when:2d')
        feeds.append({
            "nome": f"Google News ({q[:20]}...)",
            "url": f"https://news.google.com/rss/search?q={q_encoded}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        })

    return feeds

# ==============================================================================
# 5. DEDUPLICAÇÃO, TRAVA TEMPORAL E SUPABASE
# ==============================================================================
geolocator = Nominatim(user_agent="sp_alagamentos_univesp_bot")

def geocodificar(local_texto):
    try:
        busca = f"{local_texto}, São Paulo, SP, Brasil"
        location = geolocator.geocode(busca, timeout=10)
        if location and -24.1 <= location.latitude <= -23.3 and -46.9 <= location.longitude <= -46.3:
            return location.latitude, location.longitude
    except GeopyError as e:
        print(f"⚠️ Alerta na geocodificação: {e}")
    except Exception as e:
        print(f"⚠️ Erro inesperado na geocodificação: {e}")
    
    return -23.55052, -46.63330

def noticia_ja_existe(link):
    """Verifica se exatamente este link de notícia já foi cadastrado no banco."""
    try:
        endpoint = f"{SUPABASE_URL}/rest/v1/noticias_rss?link_noticia=eq.{quote(link)}&select=id"
        r = requests.get(endpoint, headers=HEADERS, timeout=10)
        if r.status_code == 200 and len(r.json()) > 0:
            return True
    except Exception:
        pass
    return False

def ja_existe_noticia_recente_no_local(bairro, horas=JANELA_HORAS_LOCAL):
    """
    TRAVA TEMPORAL DE LOCAL:
    Verifica se o mesmo local/bairro já recebeu uma notícia cadastrada
    nas últimas 'X' horas, evitando múltiplos pinos no mesmo ponto.
    """
    try:
        limite_tempo = (datetime.utcnow() - timedelta(hours=horas)).isoformat() + "Z"
        bairro_encoded = quote(bairro)
        endpoint = f"{SUPABASE_URL}/rest/v1/noticias_rss?bairro=eq.{bairro_encoded}&created_at=gt.{limite_tempo}&select=id"
        r = requests.get(endpoint, headers=HEADERS, timeout=10)
        if r.status_code == 200 and len(r.json()) > 0:
            return True
    except Exception as e:
        print(f"⚠️ Erro ao checar trava temporal de local: {e}")
    return False

def salvar_no_supabase(titulo, veiculo, link, bairro, lat, lon):
    try:
        payload = {
            "titulo": titulo[:250],
            "veiculo_imprensa": veiculo,
            "link_noticia": link,
            "bairro": bairro,
            "latitude": lat,
            "longitude": lon,
            "aprovado": False,
            "status_moderacao": "pendente"
        }
        endpoint = f"{SUPABASE_URL}/rest/v1/noticias_rss"
        r = requests.post(endpoint, json=payload, headers=HEADERS, timeout=10)
        if r.status_code in [200, 201]:
            print(f"✅ Registrado no Supabase: {titulo[:45]}... ({bairro})")
            return True
        else:
            print(f"⚠️ Resposta do Supabase ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"❌ Erro de conexão ao salvar: {e}")
    return False

# ==============================================================================
# 6. EXECUÇÃO PRINCIPAL
# ==============================================================================
def executar_coleta():
    print("🚀 Iniciando varredura com motor hídrico e trava temporal de locais...")
    feeds = obter_lista_completa_feeds()
    total_salvas = 0
    total_ignoradas_tempo = 0

    headers_req = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for f in feeds:
        print(f"📡 Monitorando: {f['nome']}...")
        try:
            resp = requests.get(f["url"], headers=headers_req, timeout=12)
            parsed = feedparser.parse(resp.content)

            for entry in parsed.entries:
                titulo = entry.get("title", "")
                resumo = entry.get("summary", "")
                link = entry.get("link", "")

                if not titulo or not link:
                    continue

                # 1. Trava de Link Único
                if noticia_ja_existe(link):
                    continue

                texto_completo = f"{titulo} {resumo}"
                
                score_conteudo = avaliar_relevancia_evento(texto_completo)
                score_geo = pontuar_local(texto_completo)
                score_total = score_conteudo + score_geo

                if score_total >= SCORE_MINIMO:
                    locais_encontrados = extrair_locais(texto_completo)
                    if locais_encontrados:
                        local_alvo = max(locais_encontrados, key=lambda x: x["peso"])["termo"].title()
                    else:
                        sub = subprefeitura_provavel(texto_completo)
                        local_alvo = f"Subprefeitura {sub.title()}" if sub else "São Paulo"

                    # 2. Trava Temporal por Local (evita repetições do mesmo local nas últimas 24h)
                    if ja_existe_noticia_recente_no_local(local_alvo, horas=JANELA_HORAS_LOCAL):
                        print(f"⏱️ Ignorado (trava 24h): {local_alvo} já possui notícia recente.")
                        total_ignoradas_tempo += 1
                        continue

                    lat, lon = geocodificar(local_alvo)

                    if salvar_no_supabase(titulo, f["nome"], link, local_alvo, lat, lon):
                        total_salvas += 1
                        time.sleep(1) # Respeita taxa limite do geocodificador

        except Exception as e:
            print(f"⚠️ Falha ao ler feed {f['nome']}: {e}")

    print(f"\n✨ Varredura concluída!")
    print(f"📌 Novas notícias cadastradas: {total_salvas}")
    print(f"⏱️ Notícias descartadas pela trava de 24h: {total_ignoradas_tempo}")

if __name__ == "__main__":
    executar_coleta()

"""
1. s01_config.py
================
Configurações compartilhadas do projeto. Não executa nenhuma análise:
apenas guarda as definições que todos os outros scripts usam.

O que está aqui:
  1. Pastas de trabalho do projeto.
  2. Endereço e acesso à fonte de dados da Receita Federal.
  3. Ordem das colunas de cada arquivo da Receita (os arquivos não têm cabeçalho).
  4. Recorte geográfico (município do Rio de Janeiro).
  5. Tabelas que traduzem códigos em descrições.
  6. Classificação das atividades econômicas (CNAE) usada nas pesquisas.

Referência do leiaute: "Novo Layout para os DADOS ABERTOS do CNPJ"
https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf
"""

# Ferramenta para montar caminhos de pastas.
from pathlib import Path

# ========================================================================
# 1. PASTAS DE TRABALHO
# ========================================================================
#
# Pasta principal do projeto (um nível acima da pasta de scripts).
RAIZ = Path(__file__).resolve().parent.parent

# Pastas de cada etapa: arquivos baixados, arquivos descompactados,
# base tratada e resultados das pesquisas.
DIR_ZIPS = RAIZ / "dados" / "01_zips"          # arquivos .zip baixados
DIR_CSVS = RAIZ / "dados" / "02_csvs"          # CSVs descompactados
DIR_BASE = RAIZ / "dados" / "03_base"          # parquets tratados (recorte RJ)
DIR_SAIDAS = RAIZ / "saidas"                   # tabelas e graficos das pesquisas

# Cria as pastas, caso ainda não existam.
for _d in (DIR_ZIPS, DIR_CSVS, DIR_BASE, DIR_SAIDAS):
    _d.mkdir(parents=True, exist_ok=True)

# Arquivo do banco de dados onde a base é montada.
BANCO_DUCKDB = DIR_BASE / "cnpj_rj.duckdb"

# ========================================================================
# 2. FONTE DOS DADOS
# ========================================================================
#
# Endereço dos arquivos da Receita Federal. Em 17/09/2026 o endereço antigo
# deixou de funcionar e os arquivos passaram para um compartilhamento público,
# que exige um código de acesso (o token abaixo).
URL_BASE = "https://arquivos.receitafederal.gov.br/public.php/webdav"
# Código de acesso ao compartilhamento.
SHARE_TOKEN = "YggdBLfdninEJX9"
# Credencial usada nos downloads (código de acesso, sem senha).
AUTH = (SHARE_TOKEN, "")

# Mês de referência dos dados. Fixado para que o resultado seja reproduzível.
COMPETENCIA = "2026-08"

# Arquivos divididos em 10 partes cada.
ARQUIVOS_PARTICIONADOS = {
    "Empresas": 10,
    "Estabelecimentos": 10,
    "Socios": 10,
}
# Arquivos publicados em parte única.
ARQUIVOS_UNICOS = [
    "Simples",
    "Cnaes",
    "Motivos",
    "Municipios",
    "Naturezas",
    "Paises",
    "Qualificacoes",
]

# Formato dos arquivos da Receita: separador, codificação e aspas.
CSV_SEP = ";"
CSV_ENCODING = "latin-1"   # ISO-8859-1
CSV_QUOTE = '"'

# ========================================================================
# 3. ORDEM DAS COLUNAS DE CADA ARQUIVO
# ========================================================================
#
# Colunas do arquivo de empresas.
COLS_EMPRESAS = [
    "cnpj_basico", "razao_social", "natureza_juridica",
    "qualificacao_responsavel", "capital_social", "porte_empresa",
    "ente_federativo_responsavel",
]

# Colunas do arquivo de estabelecimentos (matriz e filiais).
COLS_ESTABELECIMENTOS = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
    "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
    "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
    "data_inicio_atividade", "cnae_fiscal_principal", "cnae_fiscal_secundaria",
    "tipo_logradouro", "logradouro", "numero", "complemento", "bairro", "cep",
    "uf", "municipio", "ddd_1", "telefone_1", "ddd_2", "telefone_2", "ddd_fax",
    "fax", "correio_eletronico", "situacao_especial", "data_situacao_especial",
]

# Colunas do arquivo de sócios.
COLS_SOCIOS = [
    "cnpj_basico", "identificador_socio", "nome_socio_razao_social",
    "cnpj_cpf_socio", "qualificacao_socio", "data_entrada_sociedade", "pais",
    "representante_legal", "nome_representante",
    "qualificacao_representante_legal", "faixa_etaria",
]

# Colunas do arquivo de opção pelo Simples Nacional e MEI.
COLS_SIMPLES = [
    "cnpj_basico", "opcao_simples", "data_opcao_simples",
    "data_exclusao_simples", "opcao_mei", "data_opcao_mei",
    "data_exclusao_mei",
]

# Colunas das tabelas de apoio (código e descrição).
COLS_DOMINIO = ["codigo", "descricao"]   # Cnaes, Municipios, Naturezas, etc.

# Como reconhecer cada arquivo pelo nome, depois de descompactado.
GLOB_ARQUIVOS = {
    "empresas": "*.EMPRECSV",
    "estabelecimentos": "*.ESTABELE",
    "socios": "*.SOCIOCSV",
    "simples": "*SIMPLES*",
    "cnaes": "*.CNAECSV",
    "municipios": "*.MUNICCSV",
    "naturezas": "*.NATJUCSV",
    "qualificacoes": "*.QUALSCSV",
    "motivos": "*.MOTICSV",
    "paises": "*.PAISCSV",
}

# ========================================================================
# 4. RECORTE GEOGRÁFICO
# ========================================================================
#
# Estado do recorte.
UF_ALVO = "RJ"
# Código do município do Rio de Janeiro na tabela da Receita
# (não é o código do IBGE). O script s02_extracao_base.py confere esse valor.
MUNICIPIO_ALVO_CODIGO = "6001"
# Nome do município, usado nessa conferência.
MUNICIPIO_ALVO_NOME = "RIO DE JANEIRO"

# ========================================================================
# 5. TRADUÇÃO DE CÓDIGOS
# ========================================================================
#
# Situação cadastral da empresa.
SITUACAO_CADASTRAL = {
    "01": "Nula", "02": "Ativa", "03": "Suspensa",
    "04": "Inapta", "08": "Baixada",
}

# Porte da empresa.
PORTE_EMPRESA = {
    "00": "Nao informado", "01": "Microempresa",
    "03": "Empresa de pequeno porte", "05": "Demais",
}

# Matriz ou filial.
MATRIZ_FILIAL = {"1": "Matriz", "2": "Filial"}

# Tipo de sócio.
IDENTIFICADOR_SOCIO = {
    "1": "Pessoa juridica", "2": "Pessoa fisica", "3": "Estrangeiro",
}

# Faixa etária do sócio.
FAIXA_ETARIA_SOCIO = {
    "0": "Nao se aplica", "1": "0 a 12", "2": "13 a 20", "3": "21 a 30",
    "4": "31 a 40", "5": "41 a 50", "6": "51 a 60", "7": "61 a 70",
    "8": "71 a 80", "9": "Maior de 80",
}


# ========================================================================
# 6. CLASSIFICAÇÃO DAS ATIVIDADES ECONÔMICAS
# ========================================================================
#
# Cada divisão da CNAE (dois primeiros dígitos do código) recebe:
# seção, nome, posição na cadeia de suprimentos e público-alvo.
# Posições na cadeia: Primário, Transformação, Distribuição, Varejo,
# Serviços de apoio e Infraestrutura.
# Público-alvo: B2B (empresas), B2C (consumidor), B2G (governo) ou MISTO.
# O público-alvo é uma hipótese de trabalho, não uma informação do cadastro.
TAXONOMIA_CNAE = {
    # A - Agropecuária
    "01": ("A", "Agricultura, pecuaria e servicos relacionados", "Primario", "B2B"),
    "02": ("A", "Producao florestal", "Primario", "B2B"),
    "03": ("A", "Pesca e aquicultura", "Primario", "B2B"),
    # B - Indústrias extrativas
    "05": ("B", "Extracao de carvao mineral", "Primario", "B2B"),
    "06": ("B", "Extracao de petroleo e gas natural", "Primario", "B2B"),
    "07": ("B", "Extracao de minerais metalicos", "Primario", "B2B"),
    "08": ("B", "Extracao de minerais nao metalicos", "Primario", "B2B"),
    "09": ("B", "Atividades de apoio a extracao de minerais", "Servicos de apoio", "B2B"),
    # C - Indústrias de transformação
    "10": ("C", "Fabricacao de produtos alimenticios", "Transformacao", "B2B"),
    "11": ("C", "Fabricacao de bebidas", "Transformacao", "B2B"),
    "12": ("C", "Fabricacao de produtos do fumo", "Transformacao", "B2B"),
    "13": ("C", "Fabricacao de produtos texteis", "Transformacao", "B2B"),
    "14": ("C", "Confeccao de artigos do vestuario", "Transformacao", "B2B"),
    "15": ("C", "Preparacao de couros e calcados", "Transformacao", "B2B"),
    "16": ("C", "Produtos de madeira", "Transformacao", "B2B"),
    "17": ("C", "Celulose, papel e produtos de papel", "Transformacao", "B2B"),
    "18": ("C", "Impressao e reproducao de gravacoes", "Transformacao", "MISTO"),
    "19": ("C", "Coque, derivados de petroleo e biocombustiveis", "Transformacao", "B2B"),
    "20": ("C", "Produtos quimicos", "Transformacao", "B2B"),
    "21": ("C", "Produtos farmoquimicos e farmaceuticos", "Transformacao", "B2B"),
    "22": ("C", "Produtos de borracha e material plastico", "Transformacao", "B2B"),
    "23": ("C", "Produtos de minerais nao metalicos", "Transformacao", "B2B"),
    "24": ("C", "Metalurgia", "Transformacao", "B2B"),
    "25": ("C", "Produtos de metal, exceto maquinas", "Transformacao", "B2B"),
    "26": ("C", "Equipamentos de informatica e eletronicos", "Transformacao", "B2B"),
    "27": ("C", "Maquinas, aparelhos e materiais eletricos", "Transformacao", "B2B"),
    "28": ("C", "Maquinas e equipamentos", "Transformacao", "B2B"),
    "29": ("C", "Veiculos automotores, reboques e carrocerias", "Transformacao", "B2B"),
    "30": ("C", "Outros equipamentos de transporte", "Transformacao", "B2B"),
    "31": ("C", "Moveis", "Transformacao", "MISTO"),
    "32": ("C", "Produtos diversos", "Transformacao", "MISTO"),
    "33": ("C", "Manutencao e instalacao de maquinas", "Servicos de apoio", "B2B"),
    # D e E - Energia, água, esgoto e resíduos
    "35": ("D", "Eletricidade, gas e utilidades", "Infraestrutura", "MISTO"),
    "36": ("E", "Captacao e distribuicao de agua", "Infraestrutura", "MISTO"),
    "37": ("E", "Esgoto e atividades relacionadas", "Infraestrutura", "B2G"),
    "38": ("E", "Coleta e tratamento de residuos", "Infraestrutura", "B2G"),
    "39": ("E", "Descontaminacao e gestao de residuos", "Infraestrutura", "B2G"),
    # F - Construção
    "41": ("F", "Construcao de edificios", "Transformacao", "MISTO"),
    "42": ("F", "Obras de infraestrutura", "Infraestrutura", "B2G"),
    "43": ("F", "Servicos especializados para construcao", "Servicos de apoio", "MISTO"),
    # G - Comércio
    "45": ("G", "Comercio e reparacao de veiculos automotores", "Varejo", "MISTO"),
    "46": ("G", "Comercio por atacado", "Distribuicao", "B2B"),
    "47": ("G", "Comercio varejista", "Varejo", "B2C"),
    # H - Transporte e armazenagem
    "49": ("H", "Transporte terrestre", "Distribuicao", "MISTO"),
    "50": ("H", "Transporte aquaviario", "Distribuicao", "B2B"),
    "51": ("H", "Transporte aereo", "Distribuicao", "MISTO"),
    "52": ("H", "Armazenamento e apoio ao transporte", "Distribuicao", "B2B"),
    "53": ("H", "Correio e outras entregas", "Distribuicao", "MISTO"),
    # I - Alojamento e alimentação
    "55": ("I", "Alojamento", "Varejo", "B2C"),
    "56": ("I", "Alimentacao", "Varejo", "B2C"),
    # J - Informação e comunicação
    "58": ("J", "Edicao e edicao integrada a impressao", "Servicos de apoio", "MISTO"),
    "59": ("J", "Audiovisual e musica", "Servicos de apoio", "MISTO"),
    "60": ("J", "Radio e televisao", "Servicos de apoio", "MISTO"),
    "61": ("J", "Telecomunicacoes", "Infraestrutura", "MISTO"),
    "62": ("J", "Servicos de tecnologia da informacao", "Servicos de apoio", "B2B"),
    "63": ("J", "Portais e tratamento de dados", "Servicos de apoio", "B2B"),
    # K - Atividades financeiras
    "64": ("K", "Servicos financeiros", "Servicos de apoio", "MISTO"),
    "65": ("K", "Seguros e previdencia complementar", "Servicos de apoio", "MISTO"),
    "66": ("K", "Atividades auxiliares dos servicos financeiros", "Servicos de apoio", "MISTO"),
    # L - Atividades imobiliárias
    "68": ("L", "Atividades imobiliarias", "Servicos de apoio", "MISTO"),
    # M - Atividades profissionais e técnicas
    "69": ("M", "Atividades juridicas e de contabilidade", "Servicos de apoio", "B2B"),
    "70": ("M", "Sedes de empresas e consultoria em gestao", "Servicos de apoio", "B2B"),
    "71": ("M", "Servicos de arquitetura e engenharia", "Servicos de apoio", "B2B"),
    "72": ("M", "Pesquisa e desenvolvimento cientifico", "Servicos de apoio", "B2B"),
    "73": ("M", "Publicidade e pesquisa de mercado", "Servicos de apoio", "B2B"),
    "74": ("M", "Outras atividades profissionais e tecnicas", "Servicos de apoio", "B2B"),
    "75": ("M", "Atividades veterinarias", "Varejo", "B2C"),
    # N - Atividades administrativas
    "77": ("N", "Alugueis nao imobiliarios e gestao de ativos", "Servicos de apoio", "B2B"),
    "78": ("N", "Selecao e agenciamento de mao de obra", "Servicos de apoio", "B2B"),
    "79": ("N", "Agencias de viagens e operadores turisticos", "Servicos de apoio", "B2C"),
    "80": ("N", "Vigilancia, seguranca e investigacao", "Servicos de apoio", "B2B"),
    "81": ("N", "Servicos para edificios e paisagismo", "Servicos de apoio", "B2B"),
    "82": ("N", "Servicos de escritorio e apoio administrativo", "Servicos de apoio", "B2B"),
    # O - Administração pública
    "84": ("O", "Administracao publica, defesa e seguridade social", "Infraestrutura", "B2G"),
    # P - Educação
    "85": ("P", "Educacao", "Varejo", "B2C"),
    # Q - Saúde
    "86": ("Q", "Atencao a saude humana", "Varejo", "B2C"),
    "87": ("Q", "Atencao a saude com alojamento", "Varejo", "B2C"),
    "88": ("Q", "Servicos de assistencia social sem alojamento", "Varejo", "B2C"),
    # R - Artes, cultura, esporte e recreação
    "90": ("R", "Artes cenicas, espetaculos e atividades complementares", "Varejo", "B2C"),
    "91": ("R", "Patrimonio cultural e ambiental", "Varejo", "B2C"),
    "92": ("R", "Jogos de azar e apostas", "Varejo", "B2C"),
    "93": ("R", "Esportivas e de recreacao", "Varejo", "B2C"),
    # S - Outros serviços
    "94": ("S", "Organizacoes associativas", "Servicos de apoio", "MISTO"),
    "95": ("S", "Reparacao e manutencao de objetos pessoais", "Varejo", "B2C"),
    "96": ("S", "Outras atividades de servicos pessoais", "Varejo", "B2C"),
    # T e U - Serviços domésticos e organismos internacionais
    "97": ("T", "Servicos domesticos", "Varejo", "B2C"),
    "99": ("U", "Organismos internacionais", "Infraestrutura", "B2G"),
}

# Nome de cada seção da CNAE (letras A a U).
NOMES_SECAO = {
    "A": "Agropecuaria", "B": "Industrias extrativas",
    "C": "Industrias de transformacao", "D": "Eletricidade e gas",
    "E": "Agua, esgoto e residuos", "F": "Construcao", "G": "Comercio",
    "H": "Transporte e armazenagem", "I": "Alojamento e alimentacao",
    "J": "Informacao e comunicacao", "K": "Atividades financeiras",
    "L": "Atividades imobiliarias", "M": "Profissionais e tecnicas",
    "N": "Atividades administrativas", "O": "Administracao publica",
    "P": "Educacao", "Q": "Saude humana e servico social",
    "R": "Artes, cultura, esporte e recreacao", "S": "Outros servicos",
    "T": "Servicos domesticos", "U": "Organismos internacionais",
}

# Divisões da CNAE tratadas como logística na Pesquisa 2.
DIVISOES_LOGISTICA = {"49", "50", "51", "52", "53"}


# Recebe um código CNAE e devolve sua classificação:
# seção, divisão, nome, posição na cadeia e público-alvo.
def classificar_cnae(cnae7: str) -> tuple:
    # Código vazio: devolve "não classificado".
    if not cnae7:
        return ("Z", "00", "Nao classificado", "Nao classificado", "Nao classificado")
    # Pega os dois primeiros dígitos (a divisão).
    div = str(cnae7).zfill(7)[:2]
    # Divisão conhecida: devolve a classificação da tabela.
    if div in TAXONOMIA_CNAE:
        secao, nome, elo, publico = TAXONOMIA_CNAE[div]
        return (secao, div, nome, elo, publico)
    # Divisão fora da tabela: devolve "não classificado".
    return ("Z", div, "Nao classificado", "Nao classificado", "Nao classificado")

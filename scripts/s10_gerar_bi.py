"""
10. s10_gerar_bi.py
===================
Gera os 3 painéis (BI) em HTML, um por pesquisa, a partir das tabelas
produzidas pelas pesquisas 1, 2 e 3.

O que faz, em ordem:
  1. Encontra e lê as 22 tabelas (CSV) das três pesquisas.
  2. Prepara a formatação: números no padrão brasileiro e acentos nos nomes.
  3. Define o visual dos painéis (cores, fontes, tabelas e barras).
  4. Monta o painel de cada pesquisa: números principais, uma seção por
     indicador com gráfico, tabela, texto de leitura e ressalvas.
  5. Grava os três arquivos HTML.

Os arquivos abrem direto no navegador. Sem internet, o navegador apenas
troca as fontes por outras parecidas.

Como rodar:
    python s10_gerar_bi.py
    python s10_gerar_bi.py --saidas "pasta_das_saidas" --destino "pasta_dos_html"

Por padrão lê de saidas/ (definida no s01_config.py) e grava em saidas/bi/.

Requisito:
    pip install pandas
"""

# Bibliotecas usadas pelo script.
import argparse, html, sys
from pathlib import Path

import pandas as pd

# ========================================================================
# 1. LEITURA DAS TABELAS DAS PESQUISAS
# ========================================================================
#
# As 22 tabelas usadas nos painéis.
ARQUIVOS = [
    "I1a_composicao_absoluta.csv", "I2_razao_oferta_demanda.csv",
    "I3_hhi_por_secao.csv", "I4_perfil_por_orientacao.csv",
    "I5_ranking_cnae.csv", "I6_descontinuidade.csv",
    "D1_ranking_bairros.csv", "D1b_gini_locacional.csv",
    "D2b_especializacoes_locais.csv", "D3_concentracao_espacial.csv",
    "D4_matriz_filial.csv", "D5b_alcance_por_secao.csv",
    "D5c_nota_sobre_a_mediana.csv", "D6_logistica_por_bairro.csv",
    "E1a_capital_por_porte.csv", "E2b_societario_por_secao.csv",
    "E2c_faixa_etaria_socios.csv", "E3_escopo_operacional.csv",
    "E4_enquadramento_tributario.csv", "E5a_icci_por_empresa.csv",
    "E5b_icci_por_secao.csv", "E6a_perfil_clusters.csv",
]


# Pasta de resultados definida no s01_config.py (ou "saidas", se não houver).
def _pasta_padrao() -> Path:
    try:
        import s01_config as cfg
        return Path(cfg.DIR_SAIDAS)
    except Exception:
        return Path("saidas")


# Procura cada tabela dentro da pasta de resultados.
# Se faltar alguma, para e informa qual.
def localizar(saidas: Path) -> dict:
    achados, faltando = {}, []
    for nome in ARQUIVOS:
        hits = sorted(saidas.rglob(nome))
        if hits:
            achados[nome] = hits[0]
        else:
            faltando.append(nome)
    if faltando:
        sys.exit("[erro] CSVs nao encontrados em " + str(saidas) + ":\n  - "
                 + "\n  - ".join(faltando)
                 + "\nRode antes os scripts s06, s07 e s08.")
    return achados


# Lê as tabelas e guarda os dados de cada indicador.
def carregar_dados(saidas: Path) -> dict:
    a = localizar(saidas)
    rd = lambda n: pd.read_csv(a[n])
    D = {}
    # Pesquisa 1 (I1 a I6).
    D["i1"] = rd("I1a_composicao_absoluta.csv").to_dict("records")
    D["i2"] = rd("I2_razao_oferta_demanda.csv").fillna("").to_dict("records")
    D["i3"] = rd("I3_hhi_por_secao.csv").to_dict("records")
    D["i4"] = rd("I4_perfil_por_orientacao.csv").to_dict("records")
    D["i5"] = rd("I5_ranking_cnae.csv").head(20).to_dict("records")
    D["i6"] = rd("I6_descontinuidade.csv").to_dict("records")
    # Pesquisa 2 (D1 a D6).
    D["d1"] = rd("D1_ranking_bairros.csv").head(25).to_dict("records")
    D["d1b"] = rd("D1b_gini_locacional.csv").to_dict("records")
    D["d2b"] = rd("D2b_especializacoes_locais.csv").head(25).to_dict("records")
    D["d3"] = rd("D3_concentracao_espacial.csv").to_dict("records")
    D["d4"] = rd("D4_matriz_filial.csv").to_dict("records")
    D["d5b"] = rd("D5b_alcance_por_secao.csv").to_dict("records")
    D["d5c"] = rd("D5c_nota_sobre_a_mediana.csv").to_dict("records")[0]
    D["d6"] = rd("D6_logistica_por_bairro.csv").head(15).to_dict("records")
    # Pesquisa 3 (E1 a E6).
    D["e1"] = rd("E1a_capital_por_porte.csv").to_dict("records")
    D["e2b"] = rd("E2b_societario_por_secao.csv").to_dict("records")
    D["e2c"] = rd("E2c_faixa_etaria_socios.csv").to_dict("records")
    D["e3"] = rd("E3_escopo_operacional.csv").to_dict("records")
    D["e4"] = rd("E4_enquadramento_tributario.csv").to_dict("records")
    D["e5b"] = rd("E5b_icci_por_secao.csv").to_dict("records")
    D["e6"] = rd("E6a_perfil_clusters.csv").to_dict("records")
    # Conta as empresas em cada faixa do índice de capacidade.
    e5 = pd.read_csv(a["E5a_icci_por_empresa.csv"], usecols=["estrato_capacidade"])
    vc = e5["estrato_capacidade"].value_counts()
    D["e5estratos"] = [{"estrato": k, "empresas": int(v),
                        "pct": round(100 * v / len(e5), 2)} for k, v in vc.items()]
    return D


# Lê as pastas informadas ao rodar o script (opcional).
_ap = argparse.ArgumentParser(description="Gera os 3 BIs HTML das pesquisas")
_ap.add_argument("--saidas", default=None,
                 help="pasta com as saidas das pesquisas (padrao: config.DIR_SAIDAS)")
_ap.add_argument("--destino", default=None,
                 help="pasta onde gravar os HTML (padrao: <saidas>/bi)")
_args = _ap.parse_args()
# Define de onde ler e onde gravar, e cria a pasta de destino.
SAIDAS = Path(_args.saidas) if _args.saidas else _pasta_padrao()
DESTINO = Path(_args.destino) if _args.destino else SAIDAS / "bi"
DESTINO.mkdir(parents=True, exist_ok=True)

# Carrega todos os dados.
D = carregar_dados(SAIDAS)

# Os textos de leitura, os números do topo e os nomes dos perfis do E6 foram
# escritos para a base da competência 2026-08. Se a base mudar, as tabelas
# se atualizam, mas esses textos não: o aviso abaixo lembra de revisá-los.
TEXTOS_ESCRITOS_PARA = {"registros": 2_708_242, "ativos": 1_042_405,
                        "empresas": 1_006_894}
_base_atual = {
    "registros": int(sum(r["registros"] for r in D["i6"])),
    "ativos": int(next(r["Total"] for r in D["i1"] if r["elo_cadeia"] == "Total")),
    "empresas": int(sum(r["empresas"] for r in D["e5estratos"])),
}
if _base_atual != TEXTOS_ESCRITOS_PARA:
    print(f"[aviso] A base mudou desde que os textos dos paineis foram escritos "
          f"({TEXTOS_ESCRITOS_PARA} -> {_base_atual}). Revise os textos de "
          "leitura, os numeros do topo e os nomes dos perfis do E6.")

# ========================================================================
# 2. FORMATAÇÃO DE TEXTO E NÚMEROS
# ========================================================================
#
# Escreve números no padrão brasileiro (1.234,56).
def n(v, casas=0):
    if v == '' or v is None: return '—'
    try: f = float(v)
    except (TypeError, ValueError): return html.escape(str(v))
    if casas == 0: return f'{f:,.0f}'.replace(',', '.')
    s = f'{f:,.{casas}f}'
    return s.replace(',', '\x00').replace('.', ',').replace('\x00', '.')

# Nomes com acento: os dados da Receita vêm sem acentuação.
ACENTOS = {
 "Servicos de apoio":"Serviços de apoio","Distribuicao":"Distribuição",
 "Transformacao":"Transformação","Primario":"Primário","Comercio":"Comércio",
 "Industrias de transformacao":"Indústrias de transformação",
 "Industrias extrativas":"Indústrias extrativas","Educacao":"Educação",
 "Construcao":"Construção","Informacao e comunicacao":"Informação e comunicação",
 "Saude humana e servico social":"Saúde humana e serviço social",
 "Transporte e armazenagem":"Transporte e armazenagem",
 "Profissionais e tecnicas":"Profissionais e técnicas",
 "Atividades administrativas":"Atividades administrativas",
 "Atividades financeiras":"Atividades financeiras",
 "Atividades imobiliarias":"Atividades imobiliárias",
 "Alojamento e alimentacao":"Alojamento e alimentação",
 "Administracao publica":"Administração pública","Agropecuaria":"Agropecuária",
 "Agua, esgoto e residuos":"Água, esgoto e resíduos",
 "Eletricidade e gas":"Eletricidade e gás","Outros servicos":"Outros serviços",
 "Servicos domesticos":"Serviços domésticos",
 "Artes, cultura, esporte e recreacao":"Artes, cultura, esporte e recreação",
 "Organismos internacionais":"Organismos internacionais",
 "Jacarepagua":"Jacarepaguá","Meier":"Méier","Iraja":"Irajá","Paciencia":"Paciência",
 "Cidade Universitaria":"Cidade Universitária",
 "Freguesia Jacarepagua":"Freguesia (Jacarepaguá)","Taquara":"Taquara",
 "Nao se aplica":"Não se aplica","Maior de 80":"Maior de 80",
 "Media":"Média","Desconcentrado":"Desconcentrado",
 "Moderadamente concentrado":"Moderadamente concentrado",
 "indefinido: elo sem divisoes CNAE B2C/B2G":"indefinido: elo sem divisões CNAE B2C/B2G",
 "cautela: denominador < 5% do elo":"cautela: denominador < 5% do elo",
 "definido":"definido",
 "todos os rotulos":"todos os rótulos",
 "min 50 estabelecimentos":"mínimo de 50 estabelecimentos",
 "min 300 estabelecimentos":"mínimo de 300 estabelecimentos",
}
# Prepara um texto para o HTML, já com acentos.
def esc(s):
    t = str(s)
    return html.escape(ACENTOS.get(t, t))

# ========================================================================
# 3. VISUAL DOS PAINÉIS
# ========================================================================
#
# Cores, fontes e layout, com versão para tema claro e escuro.
CSS = """
:root{
  box-sizing:border-box;
  padding-top:env(safe-area-inset-top,0px);
  padding-bottom:env(safe-area-inset-bottom,0px);
  --papel:#E6E8E7; --tinta:#191F24; --fio:#C4C8C6; --fio-forte:#8E9693;
  --suave:#5C6560; --bloco:#DCDFDD;
}
:root:not([data-theme="light"]){ }
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --papel:#14181A; --tinta:#E4E7E5; --fio:#2C3337; --fio-forte:#505A5E;
    --suave:#9BA4A0; --bloco:#1C2225;
  }
}
:root[data-theme="dark"]{
  --papel:#14181A; --tinta:#E4E7E5; --fio:#2C3337; --fio-forte:#505A5E;
  --suave:#9BA4A0; --bloco:#1C2225;
}
*,*::before,*::after{box-sizing:inherit}
html{scroll-padding-top:env(safe-area-inset-top,0px);-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--papel); color:var(--tinta);
  font-family:"Source Serif 4",Georgia,"Times New Roman",serif;
  font-size:17px; line-height:1.55;
}
.wrap{max-width:1060px;margin:0 auto;padding:0 20px 90px}
h1,h2,h3,.sans,th,.num,.cod,.cifra,.etq{
  font-family:Archivo,"Helvetica Neue",Arial,sans-serif;
}
.num,.cifra,td.v{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}

/* masthead */
header.topo{border-bottom:3px solid var(--tinta);padding:40px 0 18px;margin-bottom:0}
.serie{font-family:Archivo,Arial,sans-serif;font-size:13px;letter-spacing:.14em;
  color:var(--acento);font-weight:600;margin:0 0 10px}
h1{font-size:clamp(30px,5.2vw,50px);line-height:1.04;font-weight:700;
  letter-spacing:-.022em;margin:0 0 12px;max-width:17ch}
.sub{font-size:19px;color:var(--suave);margin:0 0 26px;max-width:62ch;line-height:1.5}
.painel{display:flex;flex-wrap:wrap;gap:0;border-top:1px solid var(--fio)}
.painel div{flex:1 1 170px;padding:14px 20px 14px 0;border-right:1px solid var(--fio)}
.painel div:last-child{border-right:0}
.cifra{display:block;font-size:27px;font-weight:700;letter-spacing:-.02em;line-height:1.1}
.etq{display:block;font-size:12.5px;color:var(--suave);margin-top:3px;line-height:1.35}

/* secoes */
section{padding:46px 0 10px;border-bottom:1px solid var(--fio)}
section:last-of-type{border-bottom:0}
.cab{display:flex;gap:16px;align-items:baseline;margin-bottom:6px}
.cod{flex:0 0 auto;font-size:13px;font-weight:700;color:var(--papel);
  background:var(--acento);padding:3px 8px;border-radius:2px;letter-spacing:.04em}
h2{font-size:25px;font-weight:600;letter-spacing:-.016em;margin:0;line-height:1.2}
.leitura{color:var(--suave);max-width:70ch;margin:10px 0 24px;font-size:16.5px}
.leitura b{color:var(--tinta);font-weight:600}

/* tabelas */
.rolagem{overflow-x:auto;margin:0 -20px;padding:0 20px}
table{border-collapse:collapse;width:100%;font-size:15px;min-width:460px}
th{text-align:left;font-size:12px;font-weight:600;letter-spacing:.05em;
  color:var(--suave);padding:0 12px 7px 0;border-bottom:1.5px solid var(--fio-forte);
  vertical-align:bottom}
th.v,td.v{text-align:right;padding-right:12px}
th.v{padding-left:16px}
th.v:last-child,td.v:last-child{padding-right:0}
td{padding:8px 12px 8px 0;border-bottom:1px solid var(--fio);vertical-align:top}
td.v{padding-left:14px;white-space:nowrap}
tr:last-child td{border-bottom:0}
tbody tr.total td{border-top:1.5px solid var(--fio-forte);font-weight:700}
.rot{font-weight:600}

/* barras css */
.barras{margin:4px 0 0}
.lin{display:grid;grid-template-columns:minmax(120px,30%) 1fr auto;gap:12px;
  align-items:center;padding:6px 0;border-bottom:1px solid var(--fio)}
.lin:last-child{border-bottom:0}
.lin .nm{font-size:14.5px;line-height:1.3}
.trilho{display:flex;height:13px;background:var(--bloco)}
.barra{display:block;height:100%;background:var(--acento);min-width:2px}
.barra.alt{background:var(--acento2)}
.lin .vl{font-size:14px;font-variant-numeric:tabular-nums;white-space:nowrap;
  font-family:Archivo,Arial,sans-serif;font-weight:600}
.empilhada{display:flex;height:17px;background:var(--bloco)}
.empilhada span{height:100%}
.legenda{display:flex;flex-wrap:wrap;gap:16px;margin:14px 0 18px;font-size:13.5px;
  font-family:Archivo,Arial,sans-serif}
.legenda i{display:inline-block;width:11px;height:11px;margin-right:6px;
  vertical-align:-1px;font-style:normal}

/* nota de ressalva */
.nota{border-left:3px solid var(--acento);background:var(--bloco);
  padding:13px 16px;margin:22px 0 4px;font-size:15.5px;max-width:72ch}
.nota b{font-weight:600}
.fonte{font-size:12.5px;color:var(--suave);margin-top:14px;
  font-family:Archivo,Arial,sans-serif}

footer{padding:38px 0 0;border-top:3px solid var(--tinta);margin-top:46px;
  font-size:14px;color:var(--suave)}
footer p{margin:0 0 10px;max-width:74ch}
.navega{display:flex;gap:18px;flex-wrap:wrap;margin-top:22px;font-size:14px;
  font-family:Archivo,Arial,sans-serif}
.navega a{color:var(--acento);text-decoration:none;border-bottom:1px solid currentColor;
  padding-bottom:1px}
.navega a:hover,.navega a:focus{color:var(--tinta)}
a:focus-visible{outline:2px solid var(--acento);outline-offset:3px}
@media (max-width:620px){
  body{font-size:16px}
  .lin{grid-template-columns:1fr auto;gap:4px 10px}
  .lin .trilho{grid-column:1/-1;order:3}
  .painel div{flex:1 1 130px;padding-right:14px}
}
@media print{
  body{background:#fff;color:#000}
  .rolagem{overflow:visible}
  section{break-inside:avoid}
}
"""

# Monta a página completa: cabeçalho, números principais, seções e rodapé.
def pagina(acento, acento2, serie, titulo, sub, painel, corpo, nota_rodape, links):
    pain = ''.join(f'<div><span class="cifra">{c}</span><span class="etq">{e}</span></div>'
                   for c, e in painel)
    nav = ''.join(f'<a href="{h}">{t}</a>' for h, t in links)
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(titulo)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">
<style>:root{{--acento:{acento};--acento2:{acento2}}}{CSS}</style>
</head><body><div class="wrap">
<header class="topo">
  <p class="serie">{esc(serie)}</p>
  <h1>{esc(titulo)}</h1>
  <p class="sub">{sub}</p>
  <div class="painel">{pain}</div>
</header>
{corpo}
<footer>
{nota_rodape}
<div class="navega">{nav}</div>
</footer>
</div></body></html>"""

# Monta a seção de um indicador: título, leitura, conteúdo, ressalva e fonte.
def secao(cod, titulo, leitura, conteudo, fonte, nota=None):
    nt = f'<div class="nota">{nota}</div>' if nota else ''
    return f"""<section id="{cod.lower()}">
  <div class="cab"><span class="cod">{cod}</span><h2>{esc(titulo)}</h2></div>
  <p class="leitura">{leitura}</p>
  {conteudo}{nt}
  <p class="fonte">{fonte}</p>
</section>"""

# Aplica acentos também em nomes compostos (ex.: "Bairro · Setor").
def _ac(t):
    t = str(t)
    if ' · ' in t:
        return ' · '.join(ACENTOS.get(x, x) for x in t.split(' · '))
    return ACENTOS.get(t, t)

# Desenha um gráfico de barras simples em HTML.
def barras(itens, casas=0, sufixo='', alt=None):
    mx = max((i[1] for i in itens if isinstance(i[1], (int, float))), default=1) or 1
    out = []
    for nome, val in itens:
        pct = max(0.4, 100 * float(val) / mx)
        cls = 'barra alt' if (alt and nome in alt) else 'barra'
        out.append(f'<div class="lin"><span class="nm">{html.escape(_ac(nome))}</span>'
                   f'<span class="trilho"><span class="{cls}" style="width:{pct:.1f}%"></span></span>'
                   f'<span class="vl">{n(val, casas)}{sufixo}</span></div>')
    return '<div class="barras">' + ''.join(out) + '</div>'

# Monta uma tabela em HTML.
def tabela(colunas, linhas, total=None):
    th = ''.join(f'<th class="v">{esc(c[0])}</th>' if c[1] else f'<th>{esc(c[0])}</th>'
                 for c in colunas)
    body = []
    for ln in linhas:
        tds = ''.join(f'<td class="v">{v}</td>' if c[1] else
                      f'<td class="rot">{v}</td>' if i == 0 else f'<td>{v}</td>'
                      for i, (v, c) in enumerate(zip(ln, colunas)))
        body.append(f'<tr>{tds}</tr>')
    if total:
        tds = ''.join(f'<td class="v">{v}</td>' if c[1] else f'<td>{v}</td>'
                      for v, c in zip(total, colunas))
        body.append(f'<tr class="total">{tds}</tr>')
    return ('<div class="rolagem"><table><thead><tr>' + th +
            '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>')

# Texto de fonte e rodapé comum aos três painéis.
FONTE = ('Fonte: elaborado pelo autor a partir dos Dados Abertos do CNPJ, '
         'Receita Federal do Brasil, competência 2026-08.')
RODAPE_COMUM = """<p>Município do Rio de Janeiro, código 6001 da tabela de municípios da
Receita Federal. Universo de 2.708.242 estabelecimentos registrados, dos quais
1.042.405 com situação cadastral ativa. Salvo indicação em contrário, os
indicadores usam apenas os ativos.</p>
<p>O cadastro de CNPJ é administrativo e mantido para fins tributários. Não contém
demonstrações contábeis, faturamento, imobilizado ou número de empregados, e
situação cadastral ativa não implica operação econômica efetiva.</p>"""

# ========================================================================
# 4. PAINEL DA PESQUISA 1 - DIMENSÃO COMERCIAL
# ========================================================================
#
# Públicos-alvo e suas cores no gráfico do I1.
ORI = ['B2B', 'B2C', 'B2G', 'MISTO']
CORES = {'B2B': 'var(--acento)', 'B2C': '#C98A3C', 'B2G': '#5B6E52', 'MISTO': '#8E8073'}
# I1: separa a linha de total e ordena as posições da cadeia.
i1 = [r for r in D['i1'] if r['elo_cadeia'] != 'Total']
i1t = [r for r in D['i1'] if r['elo_cadeia'] == 'Total'][0]
i1 = sorted(i1, key=lambda r: -r['Total'])

# I1: barras empilhadas por público-alvo, legenda e tabela.
emp = []
for r in i1:
    segs = ''.join(
        f'<span style="width:{100*r[o]/r["Total"]:.2f}%;background:{CORES[o]}"></span>'
        for o in ORI if r[o] > 0)
    emp.append(f'<div class="lin"><span class="nm">{esc(r["elo_cadeia"])}</span>'
               f'<span class="empilhada" style="width:{100*r["Total"]/i1t["Total"]:.1f}%">{segs}</span>'
               f'<span class="vl">{n(r["Total"])}</span></div>')
leg = ''.join(f'<span><i style="background:{CORES[o]}"></i>{o}</span>' for o in ORI)
c_i1 = (f'<div class="legenda">{leg}</div><div class="barras">' + ''.join(emp) + '</div>' +
        tabela([('Elo da cadeia', 0), ('B2B', 1), ('B2C', 1), ('B2G', 1), ('MISTO', 1), ('Total', 1)],
               [[esc(r['elo_cadeia']), n(r['B2B']), n(r['B2C']), n(r['B2G']), n(r['MISTO']), n(r['Total'])] for r in i1],
               total=['Total', n(i1t['B2B']), n(i1t['B2C']), n(i1t['B2G']), n(i1t['MISTO']), n(i1t['Total'])]))

# I2: tabela de oferta e demanda.
c_i2 = tabela([('Elo da cadeia', 0), ('Ofertantes B2B', 1), ('Demandantes B2C/B2G', 1),
               ('Razão', 1), ('Situação do indicador', 0)],
              [[esc(r['elo_cadeia']), n(r['ofertantes_b2b']), n(r['demandantes_b2c_b2g']),
                n(r['razao_oferta_demanda'], 3), esc(r['situacao_indicador'])] for r in D['i2']])

# I3: barras e tabela de concentração (setores moderados em outra cor).
i3o = sorted(D['i3'], key=lambda r: -r['estabelecimentos'])[:14]
c_i3 = (barras([(r['secao_desc'], r['hhi']) for r in i3o], 1,
               alt={r['secao_desc'] for r in i3o if r['hhi'] >= 1500}) +
        tabela([('Seção CNAE', 0), ('Estabelecimentos', 1), ('CNAEs', 1), ('HHI', 1),
                ('Atividade dominante', 1), ('Classificação', 0)],
               [[esc(r['secao_desc']), n(r['estabelecimentos']), n(r['cnaes_distintos']),
                 n(r['hhi'], 1), n(r['share_dominante_pct'], 2) + '%', esc(r['classificacao'])]
                for r in i3o]))

# I4: tabela de perfil por público-alvo.
c_i4 = tabela([('Orientação', 0), ('Estabelecimentos', 1), ('Microempresa', 1), ('MEI', 1),
               ('Capital mediano', 1), ('Idade mediana', 1), ('CNAEs sec.', 1)],
              [[esc(r['orientacao']), n(r['estabelecimentos']), n(r['pct_microempresa'], 2) + '%',
                n(r['pct_mei'], 2) + '%', 'R$ ' + n(r['capital_mediano']),
                n(r['idade_mediana_anos'], 2) + ' anos', n(r['cnaes_secundarios_medio'], 2)]
               for r in D['i4']])

# I5: barras e tabela das atividades mais frequentes.
c_i5 = (barras([(r['cnae_desc'][:52], r['estabelecimentos']) for r in D['i5'][:12]]) +
        tabela([('Atividade', 0), ('Elo', 0), ('Orientação', 0), ('Estabelecimentos', 1),
                ('Participação', 1), ('Acumulado', 1)],
               [[esc(r['cnae_desc'][:60]), esc(r['elo_cadeia']), esc(r['orientacao']),
                 n(r['estabelecimentos']), n(r['share_pct'], 2) + '%',
                 n(r['share_acumulado_pct'], 2) + '%'] for r in D['i5']]))

# I6: barras e tabela de encerramento cadastral.
i6 = D['i6']
c_i6 = (barras([(f"{r['elo_cadeia']} · {r['orientacao']}", r['taxa_descontinuidade_pct'])
                for r in i6], 2, '%') +
        tabela([('Elo · orientação', 0), ('Registros', 1), ('Ativos', 1),
                ('Baixados ou inaptos', 1), ('Taxa', 1)],
               [[html.escape(_ac(f"{r['elo_cadeia']} · {r['orientacao']}")), n(r['registros']), n(r['ativos']),
                 n(r['baixados_ou_inaptos']), n(r['taxa_descontinuidade_pct'], 2) + '%'] for r in i6]))

# Junta as seis seções, com textos de leitura e ressalvas.
corpo1 = ''.join([
  secao('I1', 'Composição por elo da cadeia e público-alvo',
        'Varejo e serviços de apoio concentram <b>82,03%</b> dos estabelecimentos ativos. '
        'Três elos — primário, transformação e distribuição — não têm nenhum estabelecimento '
        'voltado ao consumidor final ou ao setor público, o que condiciona a leitura do indicador seguinte.',
        c_i1, FONTE),
  secao('I2', 'Oferta e demanda potencial por elo',
        'A razão entre ofertantes B2B e demandantes compara a oferta local de fornecimento '
        'empresarial com a demanda potencial dentro do mesmo elo.',
        c_i2, FONTE,
        'Limitação do indicador. Como a taxonomia atribui orientação no nível da divisão CNAE, '
        'e as divisões de primário, transformação e distribuição são integralmente B2B ou mistas, '
        'o denominador zera nesses três elos e a razão fica indefinida — por desenho, não por erro '
        'de cálculo. Em serviços de apoio o denominador representa menos de 5% do elo, inflando o '
        'valor para 40,339. <b>A razão intra-elo só é interpretável em varejo e infraestrutura.</b>'),
  secao('I3', 'Concentração setorial (Herfindahl-Hirschman)',
        'O índice mede a concentração das atividades dentro de cada seção CNAE. '
        'Valores abaixo de 1.500 indicam setor desconcentrado; entre 1.500 e 2.500, moderadamente '
        'concentrado. <b>Nenhuma seção do município atinge a faixa de alta concentração.</b> '
        'Barras em tom distinto marcam as seções moderadamente concentradas.',
        c_i3, FONTE),
  secao('I4', 'Perfil por orientação de público',
        'O fornecedor do setor público é a categoria destoante: capital mediano mais alto, '
        'idade mediana de <b>10,67 anos</b> contra 4 a 5 anos nas demais, e a menor participação '
        'de microempresas e MEI. A barreira de entrada à demanda pública aparece no cadastro.',
        c_i4, FONTE),
  secao('I5', 'Atividades econômicas mais frequentes',
        'A atividade isolada mais frequente do município é <b>cabeleireiros, manicure e pedicure</b>, '
        'com 4,33% dos ativos. As vinte primeiras somam pouco mais de um terço do tecido, '
        'o que é coerente com o quadro de baixa concentração medido no indicador anterior.',
        c_i5, FONTE),
  secao('I6', 'Descontinuidade cadastral por elo',
        'Proporção de registros baixados ou inaptos sobre o total de registros de cada combinação. '
        'A distribuição B2B é o elo que mais encerra, com <b>71,67%</b>, e os serviços de apoio B2B '
        'o que menos encerra, com 51,09%.',
        c_i6, FONTE,
        'Este indicador usa o <b>universo completo</b> de 2.708.242 registros como denominador, e não '
        'apenas os ativos. Encerramento cadastral não equivale a encerramento de atividade econômica.'),
])

# Monta a página da Pesquisa 1.
html1 = pagina(
  '#9A5B18', '#C98A3C',
  'Pesquisa 1 de 3',
  'A dimensão comercial do tecido empresarial carioca',
  'Como se distribuem os públicos de compra e venda entre as empresas do município do Rio de '
  'Janeiro, e que desequilíbrios entre oferta e demanda potencial esse arranjo revela.',
  [('1.042.405', 'estabelecimentos ativos'), ('82,03%', 'em varejo e serviços de apoio'),
   ('45,38%', 'voltados ao consumidor final'), ('2.237,7', 'maior HHI setorial')],
  corpo1, RODAPE_COMUM,
  [('#i1', 'I1 Composição'), ('#i2', 'I2 Oferta e demanda'), ('#i3', 'I3 Concentração'),
   ('#i4', 'I4 Perfil'), ('#i5', 'I5 Atividades'), ('#i6', 'I6 Descontinuidade')])
# Grava o arquivo HTML.
open(DESTINO / 'bi_pesquisa_1_comercial.html', 'w', encoding='utf-8').write(html1)
print('[ok]', DESTINO / 'bi_pesquisa_1_comercial.html')

# ========================================================================
# 5. PAINEL DA PESQUISA 2 - DISTRIBUIÇÃO FÍSICA
# ========================================================================
#
# D1: barras e tabela dos bairros.
d1 = D['d1']
c_d1 = (barras([(r['bairro_norm'].title(), r['estabelecimentos']) for r in d1[:15]]) +
        tabela([('Bairro', 0), ('Estabelecimentos', 1), ('Matrizes', 1), ('Capital mediano', 1),
                ('Idade mediana', 1), ('Participação', 1), ('Acumulado', 1)],
               [[esc(r['bairro_norm'].title()), n(r['estabelecimentos']), n(r['pct_matriz'], 2) + '%',
                 'R$ ' + n(r['capital_mediano']), n(r['idade_mediana_anos'], 2) + ' anos',
                 n(r['share_municipio_pct'], 2) + '%', n(r['share_acumulado_pct'], 2) + '%']
                for r in d1]))

# D1b: tabela do índice de Gini nos três cortes.
d1b = D['d1b']
c_d1b = tabela([('Corte adotado', 0), ('Bairros', 1), ('Estabelecimentos cobertos', 1),
                ('Cobertura', 1), ('Gini locacional', 1)],
               [[esc(r['corte'].replace('_', ' ')) + (' — adotado' if r['principal'] else ''),
                 n(r['bairros_considerados']), n(r['estabelecimentos_cobertos']),
                 n(r['cobertura_pct'], 3) + '%', n(r['gini_locacional'], 4)] for r in d1b])

# D2: barras e tabela das especializações dos bairros.
c_d2 = (barras([(f"{r['bairro_norm'].title()} · {r['secao_desc']}", r['ql'])
                for r in D['d2b'][:14]], 2) +
        tabela([('Bairro', 0), ('Seção CNAE', 0), ('QL', 1), ('Estabelecimentos', 1)],
               [[esc(r['bairro_norm'].title()), esc(r['secao_desc']), n(r['ql'], 3),
                 n(r['estabelecimentos'])] for r in D['d2b']]))

# D3: tabela de concentração de cada setor no território.
d3 = sorted(D['d3'], key=lambda r: -r['hhi_locacional'])[:14]
c_d3 = tabela([('Seção CNAE', 0), ('Estabelecimentos', 1), ('Bairros ocupados', 1),
               ('HHI locacional', 1), ('Top 3 bairros', 1), ('Bairro principal', 0)],
              [[esc(r['secao_desc']), n(r['estabelecimentos']), n(r['bairros_ocupados']),
                n(r['hhi_locacional'], 1), n(r['share_top3_bairros_pct'], 2) + '%',
                esc(r['bairro_principal'].title())] for r in d3])

# D4: barras e tabela de filiais por setor.
d4 = sorted(D['d4'], key=lambda r: -r['pct_filial'])[:14]
c_d4 = (barras([(r['secao_desc'], r['pct_filial']) for r in d4], 2, '%') +
        tabela([('Seção CNAE', 0), ('Estabelecimentos', 1), ('Matrizes', 1), ('Filiais', 1), ('Filiais', 1)],
               [[esc(r['secao_desc']), n(r['estabelecimentos']), n(r['matrizes']),
                 n(r['filiais']), n(r['pct_filial'], 2) + '%'] for r in d4]))

# D5: barras e tabela de alcance interestadual.
d5 = sorted(D['d5b'], key=lambda r: -r['pct_interestadual'])[:14]
c_d5 = (barras([(r['secao_desc'], r['pct_interestadual']) for r in d5], 2, '%') +
        tabela([('Seção CNAE', 0), ('Empresas', 1), ('Unidades médias', 1), ('Unidades máx.', 1),
                ('Multiunidade', 1), ('Interestadual', 1), ('Índice p99', 1)],
               [[esc(r['secao_desc']), n(r['empresas']), n(r['unidades_medias'], 2),
                 n(r['unidades_max']), n(r['pct_multiunidade'], 2) + '%',
                 n(r['pct_interestadual'], 2) + '%', n(r['indice_alcance_p99'], 2)] for r in d5]))

# D6: tabela de logística por bairro.
c_d6 = tabela([('Bairro', 0), ('Estabelecimentos logísticos', 1), ('Total do bairro', 1),
               ('Intensidade', 1), ('Capital mediano', 1)],
              [[esc(r['bairro_norm'].title()), n(r['estabelecimentos_logisticos']),
                n(r['total_bairro']), n(r['intensidade_logistica_pct'], 2) + '%',
                'R$ ' + n(r['capital_mediano'])] for r in D['d6']])

# Junta as sete seções, com textos de leitura e ressalvas.
corpo2 = ''.join([
  secao('D1', 'Distribuição dos estabelecimentos por bairro',
        'Os dez bairros mais densos concentram <b>36,47%</b> dos estabelecimentos ativos. '
        'Centro, Barra da Tijuca e Campo Grande lideram, mas por razões distintas: o Centro tem '
        'a maior idade mediana e o maior capital mediano; Campo Grande tem a maior dispersão de CEPs.',
        c_d1, FONTE),
  secao('D1b', 'Concentração territorial e o corte de bairros',
        'O índice de Gini locacional resume em um número o grau de desigualdade na distribuição '
        'dos estabelecimentos entre bairros. O valor varia fortemente conforme o corte adotado, '
        'e a escolha do corte é uma decisão metodológica, não um detalhe de implementação.',
        c_d1b, FONTE,
        'O campo de bairro é de preenchimento livre e gera 1.333 rótulos distintos para um município '
        'de cerca de 160 bairros. Calculado sobre todos os rótulos, o índice chega a <b>0,9458</b> e '
        'sugere desigualdade extrema — mas o valor está inflado por variação ortográfica, não por '
        'concentração econômica. O corte de 300 estabelecimentos produz 161 rótulos, cobre 99,43% do '
        'município e resulta em <b>0,5710</b>, concentração moderada. É esse o valor adotado.'),
  secao('D2', 'Especializações produtivas locais',
        'O quociente locacional compara a participação de uma seção econômica no bairro com sua '
        'participação no município. Valores acima de 1,25 indicam especialização. '
        '<b>Botafogo com atividades financeiras</b> é o achado mais robusto: QL de 11,901 sobre '
        '12.513 estabelecimentos — especialização forte com massa relevante, e não efeito de amostra pequena.',
        c_d2, FONTE,
        'Quocientes muito altos sobre poucas centenas de estabelecimentos, como Santo Cristo em '
        'eletricidade e gás, devem ser lidos com cautela: o indicador é sensível a denominadores pequenos.'),
  secao('D3', 'Concentração espacial por seção econômica',
        'Enquanto o quociente locacional pergunta se uma atividade está concentrada em determinado '
        'bairro, este indicador pergunta o oposto: se a atividade se aglomera em poucos bairros ou '
        'se espalha pelo município. <b>Indústrias extrativas</b> são a seção mais aglomerada, com '
        '74,49% em apenas três bairros.',
        c_d3, FONTE),
  secao('D4', 'Estrutura matriz e filial',
        'A proporção de filiais funciona como indicador de centralização decisória. '
        '<b>Administração pública</b> destoa com 60,12% de filiais, coerente com autarquias e '
        'agências descentralizadas. No comércio, a proporção cai para 6,32%.',
        c_d4, FONTE),
  secao('D5', 'Alcance geográfico das redes com sede no município',
        'Entre as empresas cuja matriz está no município, mede-se quantas operam unidades fora '
        'do estado. <b>Eletricidade e gás</b> tem 45,02% de empresas interestaduais; no comércio, '
        'apenas 0,99%.',
        c_d5, FONTE,
        'A mediana do índice de alcance é inútil aqui: como 98,44% das empresas operam uma única '
        'unidade e 99,39% atuam em uma só unidade federativa, a mediana vale ln(2)×2 ≈ 1,386 em '
        '<b>todas</b> as seções e não discrimina nada. A leitura correta usa o percentual '
        'interestadual e os percentis superiores.'),
  secao('D6', 'Infraestrutura logística por bairro',
        'A intensidade logística mede quanto do tecido de cada bairro é formado por transporte e '
        'armazenagem. O padrão é periférico: <b>Pavuna</b> lidera em intensidade, com 17,74%, '
        'enquanto o Centro, sétimo em volume absoluto, tem apenas 3,12%.',
        c_d6, FONTE),
])

# Monta a página da Pesquisa 2.
html2 = pagina(
  '#15605C', '#4E9A8F',
  'Pesquisa 2 de 3',
  'Distribuição física e alcance de negócio',
  'Como as atividades econômicas se dispõem no território do município, que especializações '
  'locais emergem dessa distribuição, e qual o alcance geográfico das empresas ali sediadas.',
  [('0,5710', 'Gini locacional'), ('161', 'bairros no recorte'),
   ('36,47%', 'nos dez maiores bairros'), ('98,44%', 'com unidade única')],
  corpo2, RODAPE_COMUM,
  [('#d1', 'D1 Bairros'), ('#d1b', 'D1b Gini'), ('#d2', 'D2 Especializações'),
   ('#d3', 'D3 Aglomeração'), ('#d4', 'D4 Matriz e filial'), ('#d5', 'D5 Alcance'),
   ('#d6', 'D6 Logística')])
# Grava o arquivo HTML.
open(DESTINO / 'bi_pesquisa_2_distribuicao.html', 'w', encoding='utf-8').write(html2)
print('[ok]', DESTINO / 'bi_pesquisa_2_distribuicao.html')

# ========================================================================
# 6. PAINEL DA PESQUISA 3 - INFRAESTRUTURA E CAPACIDADE
# ========================================================================
#
# E1: tabela de capital social por porte.
e1 = D['e1']
c_e1 = tabela([('Porte', 0), ('Empresas', 1), ('Q25', 1), ('Mediana', 1), ('Q75', 1),
               ('P95', 1), ('Média', 1)],
              [[esc(r['porte_desc']), n(r['empresas']), 'R$ ' + n(r['q25']),
                'R$ ' + n(r['mediana']), 'R$ ' + n(r['q75']), 'R$ ' + n(r['p95']),
                'R$ ' + n(r['media'])] for r in e1])

# E2: barras e tabela do quadro de sócios.
e2 = sorted(D['e2b'], key=lambda r: -r['empresas'])[:14]
c_e2 = (barras([(r['secao_desc'], r['pct_socio_unico']) for r in e2], 2, '%') +
        tabela([('Seção CNAE', 0), ('Empresas', 1), ('Sócio único', 1), ('Com sócio PJ', 1),
                ('Capital por sócio', 1)],
               [[esc(r['secao_desc']), n(r['empresas']), n(r['pct_socio_unico'], 2) + '%',
                 n(r['pct_com_socio_pj'], 2) + '%', 'R$ ' + n(r['capital_por_socio_mediano'])]
                for r in e2]))

# E2c: barras de faixa etária dos sócios.
c_e2c = barras([(r['faixa_etaria_desc'], r['percentual']) for r in D['e2c']], 2, '%')

# E3: barras e tabela de amplitude de atuação.
e3 = sorted(D['e3'], key=lambda r: -r['cnaes_secundarios_medio'])[:14]
c_e3 = (barras([(r['secao_desc'], r['cnaes_secundarios_medio']) for r in e3], 2) +
        tabela([('Seção CNAE', 0), ('Empresas', 1), ('CNAEs sec. médio', 1),
                ('Escopo ampliado', 1), ('Multiunidade', 1), ('Idade mediana', 1)],
               [[esc(r['secao_desc']), n(r['empresas']), n(r['cnaes_secundarios_medio'], 2),
                 n(r['pct_com_escopo_ampliado'], 2) + '%', n(r['pct_multiunidade'], 2) + '%',
                 n(r['idade_mediana'], 2) + ' anos'] for r in e3]))

# E4: tabela de Simples Nacional e MEI.
e4 = sorted(D['e4'], key=lambda r: -r['pct_mei'])[:14]
c_e4 = tabela([('Seção CNAE', 0), ('Estabelecimentos', 1), ('Simples Nacional', 1),
               ('MEI', 1), ('Capital mediano', 1)],
              [[esc(r['secao_desc']), n(r['estabelecimentos']), n(r['pct_simples'], 2) + '%',
                n(r['pct_mei'], 2) + '%', 'R$ ' + n(r['capital_mediano'])] for r in e4])

# E5: barras das faixas do índice e tabela por setor.
est = D['e5estratos']
ordem = ['Muito baixa', 'Baixa', 'Media', 'Alta', 'Muito alta']
est = sorted(est, key=lambda r: ordem.index(r['estrato']) if r['estrato'] in ordem else 9)
c_e5a = barras([(r['estrato'], r['empresas']) for r in est])
e5 = sorted(D['e5b'], key=lambda r: -r['icci_mediano'])[:14]
c_e5 = c_e5a + tabela([('Seção CNAE', 0), ('Empresas', 1), ('ICCI mediano', 1),
                       ('ICCI p90', 1), ('Alta capacidade', 1)],
                      [[esc(r['secao_desc']), n(r['empresas']), n(r['icci_mediano'], 3),
                        n(r['icci_p90'], 3), n(r['pct_alta_capacidade'], 2) + '%'] for r in e5])

# E6: nomes dos cinco perfis, barras e tabela.
e6 = sorted(D['e6'], key=lambda r: -r['participacao_pct'])
ROTULOS = {1: 'Microempresa recente, escopo único', 0: 'Microempresa com escopo ampliado',
           4: 'Sociedade madura, capital maior', 3: 'Capital simbólico',
           2: 'Registro antigo, capital nulo'}
c_e6 = (barras([(ROTULOS.get(r['cluster'], str(r['cluster'])), r['empresas']) for r in e6]) +
        tabela([('Perfil', 0), ('Empresas', 1), ('Participação', 1), ('Capital mediano', 1),
                ('CNAEs sec.', 1), ('Idade mediana', 1), ('Sócios', 1)],
               [[esc(ROTULOS.get(r['cluster'], str(r['cluster']))), n(r['empresas']),
                 n(r['participacao_pct'], 2) + '%',
                 'R$ ' + n(round(2.718281828 ** r['mediana_log_capital'] - 1)),
                 n(r['mediana_qtd_cnae_secundario']), n(r['mediana_idade_anos'], 2) + ' anos',
                 n(r['mediana_qtd_socios'])] for r in e6]))

# Junta as sete seções, com textos de leitura e ressalvas.
corpo3 = ''.join([
  secao('E1', 'Capital social declarado por porte',
        'A distância entre mediana e média expõe a assimetria da variável. Nas empresas de porte '
        '"demais", a mediana é de <b>R$ 1.000</b> e a média, de <b>R$ 20,7 milhões</b> — '
        'uma diferença de quatro ordens de grandeza, produzida por uma cauda de poucos valores extremos.',
        c_e1, FONTE,
        'Essa assimetria é a razão de todo índice construído sobre capital social neste trabalho '
        'aplicar transformação logarítmica e truncamento de escores. Sem esse tratamento, poucas '
        'empresas determinariam qualquer resultado agregado.'),
  secao('E2', 'Estrutura do quadro societário',
        'O sócio único predomina em todo o tecido, variando de <b>60,03%</b> em saúde a '
        '<b>96,60%</b> em transporte e armazenagem. A presença de sócio pessoa jurídica, indicador '
        'de estrutura de capital mais complexa, é residual na maioria das seções e chega a 14,06% na saúde.',
        c_e2, FONTE),
  secao('E2c', 'Faixa etária dos sócios',
        'Mais de <b>70%</b> dos vínculos societários pertencem a pessoas com mais de 40 anos, e '
        '17,80% a pessoas acima de 70. Sócios com até 30 anos representam 4,63% do total.',
        c_e2c, FONTE +
        ' Dados agregados; a base não contém nome nem CPF de sócio pessoa física.'),
  secao('E3', 'Escopo operacional declarado',
        'A quantidade de CNAEs secundários funciona como aproximação da amplitude de atuação. '
        '<b>Informação e comunicação</b> lidera com 4,15 em média, e 54,80% dessas empresas '
        'declaram escopo ampliado, com três ou mais atividades secundárias.',
        c_e3, FONTE),
  secao('E4', 'Enquadramento tributário por seção',
        'A opção pelo Simples Nacional ou pelo MEI serve como aproximação indireta de porte de '
        'receita, por força dos limites legais de cada regime. <b>Serviços domésticos</b> é quase '
        'integralmente MEI, com 94,46%; o comércio fica em 48,11%, com capital mediano dez vezes maior.',
        c_e4, FONTE),
  secao('E5', 'Índice Composto de Capacidade Instalada',
        'O índice combina cinco variáveis cadastrais padronizadas — capital social, unidades, '
        'escopo, maturidade e quadro societário — em um escore único, sobre o qual as empresas são '
        'estratificadas. <b>Eletricidade e gás</b> tem o maior índice mediano; atividades '
        'imobiliárias têm a maior proporção de empresas em alta capacidade, 68,20%.',
        c_e5, FONTE,
        'Os pesos do índice refletem julgamento do pesquisador sobre a importância relativa de cada '
        'aproximação, e não um procedimento estatístico de ponderação. Pesos diferentes produziriam '
        'estratificação distinta.'),
  secao('E6', 'Perfis de empresa por agrupamento',
        'A segmentação aplica o mesmo tratamento de cauda do índice e separa cinco perfis com massa '
        'e leitura econômica distintas. O maior deles, com <b>46,55%</b> das empresas, é de '
        'microempresas recentes de atividade única.',
        c_e6, FONTE),
])

# Monta a página da Pesquisa 3, com a advertência sobre as aproximações.
html3 = pagina(
  '#5C3250', '#9B6A89',
  'Pesquisa 3 de 3',
  'Infraestrutura e capacidade instalada',
  'Que perfis de capacidade instalada podem ser inferidos a partir de variáveis cadastrais, '
  'e como esses perfis se diferenciam entre setores de atividade.',
  [('1.006.894', 'empresas no índice'), ('R$ 1.000 · R$ 20,7 mi', 'mediana e média, porte "demais"'),
   ('83–97%', 'com sócio único'), ('5', 'perfis identificados')],
  corpo3,
  RODAPE_COMUM + """<p><b>Advertência metodológica.</b> O cadastro não mede ativos, imobilizado
nem faturamento. Todas as variáveis desta pesquisa são aproximações cadastrais de capacidade
instalada, não mensuração direta de patrimônio. Cada conclusão deve ser lida nesses termos.</p>""",
  [('#e1', 'E1 Capital'), ('#e2', 'E2 Quadro societário'), ('#e2c', 'E2c Faixa etária'),
   ('#e3', 'E3 Escopo'), ('#e4', 'E4 Tributário'), ('#e5', 'E5 Índice'), ('#e6', 'E6 Perfis')])
# Grava o arquivo HTML.
open(DESTINO / 'bi_pesquisa_3_infraestrutura.html', 'w', encoding='utf-8').write(html3)
print('[ok]', DESTINO / 'bi_pesquisa_3_infraestrutura.html')

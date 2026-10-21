"""
7. s07_pesquisa_distribuicao.py
===============================
Pesquisa 2 - Distribuição física.

Pergunta: como as atividades econômicas se distribuem pelo território do
município, que especializações locais aparecem, e qual o alcance
geográfico das empresas sediadas no município?

Indicadores produzidos:
  D1   Ranking de bairros por número de estabelecimentos
  D1b  Concentração territorial (índice de Gini e curva de Lorenz)
  D2   Especialização de cada bairro em cada setor (quociente locacional)
  D3   Quanto cada setor se concentra em poucos bairros
  D4   Proporção de matrizes e filiais por setor
  D5   Alcance geográfico das empresas com sede no município
  D6   Peso da logística em cada bairro

Usa só estabelecimentos ativos.

Observação: o bairro é digitado livremente no cadastro, com grafias
variadas. Por isso os nomes são padronizados antes das contagens, e os
cálculos por bairro consideram apenas bairros com pelo menos 300
estabelecimentos.

Saídas (tabelas e gráficos): saidas/pesquisa_2_distribuicao/

Como rodar:
    python s07_pesquisa_distribuicao.py
"""

# Bibliotecas usadas pelo script.
from __future__ import annotations

import re
import unicodedata

import matplotlib
# Gera os gráficos direto em arquivo, sem abrir janela.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configurações do projeto (pastas, códigos e classificação CNAE).
import s01_config as cfg

# Pasta onde os resultados desta pesquisa são gravados.
SAIDA = cfg.DIR_SAIDAS / "pesquisa_2_distribuicao"
SAIDA.mkdir(parents=True, exist_ok=True)

# Aparência padrão dos gráficos.
plt.rcParams.update({"figure.dpi": 160, "font.size": 9,
                     "axes.grid": True, "grid.alpha": 0.3})

# Mínimo de estabelecimentos para um bairro entrar nos cálculos
# de concentração (D1b) e especialização (D2). O mesmo corte vale para os dois.
MINIMO_BAIRRO = 300

# Grafias alternativas frequentes e o nome padronizado de cada bairro.
SINONIMOS_BAIRRO = {
    "CENTRO RJ": "CENTRO",
    "BARRA DA TIJUCA RJ": "BARRA DA TIJUCA",
    "JACAREPAGUA RJ": "JACAREPAGUA",
    "COPACABANA RJ": "COPACABANA",
    "SAO CRISTOVAO": "SAO CRISTOVAO",
    "STA TERESA": "SANTA TERESA",
    "STO CRISTO": "SANTO CRISTO",
    "V ISABEL": "VILA ISABEL",
    "RECREIO": "RECREIO DOS BANDEIRANTES",
}


# ========================================================================
# PADRONIZAÇÃO DOS NOMES DE BAIRRO
# ========================================================================
def normalizar_bairro(valor: str | None) -> str:
    # Bairro vazio: marca como "não informado".
    if not valor or not isinstance(valor, str):
        return "NAO INFORMADO"
    # Tira acentos e põe em maiúsculas.
    txt = unicodedata.normalize("NFKD", valor)
    txt = txt.encode("ascii", "ignore").decode("ascii").upper()
    # Tira pontuação, a palavra "bairro" e espaços repetidos.
    txt = re.sub(r"[^A-Z0-9 ]", " ", txt)
    txt = re.sub(r"\b(BAIRRO|BRO|B)\b", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    # Troca grafias alternativas pelo nome padrão.
    txt = SINONIMOS_BAIRRO.get(txt, txt)
    return txt or "NAO INFORMADO"


# ========================================================================
# LEITURA DOS DADOS
# ========================================================================
def carregar() -> pd.DataFrame:
    # Lê a base analítica.
    df = pd.read_parquet(cfg.DIR_BASE / "base_analitica.parquet")
    # Classifica cada atividade pela tabela CNAE do s01_config.py.
    classes = df["cnae_fiscal_principal"].apply(cfg.classificar_cnae)
    df[["secao", "divisao", "divisao_desc", "elo_cadeia", "orientacao"]] = (
        pd.DataFrame(classes.tolist(), index=df.index)
    )
    df["secao_desc"] = df["secao"].map(cfg.NOMES_SECAO).fillna("Nao classificado")
    # Padroniza o bairro e separa o início do CEP.
    df["bairro_norm"] = df["bairro"].apply(normalizar_bairro)
    df["cep_prefixo"] = df["cep"].str.slice(0, 5)
    # Marca os ativos e as matrizes.
    df["ativa"] = df["situacao_cadastral"].eq("02")
    df["e_matriz"] = df["identificador_matriz_filial"].eq("1")
    return df


# ========================================================================
# D1 E D1b - DISTRIBUIÇÃO POR BAIRRO E CONCENTRAÇÃO TERRITORIAL
# ========================================================================
def d1_bairros(ativos: pd.DataFrame) -> pd.DataFrame:
    # Para cada bairro: estabelecimentos, matrizes, capital, idade e CEPs.
    tab = ativos.groupby("bairro_norm").agg(
        estabelecimentos=("cnpj_completo", "count"),
        matrizes=("e_matriz", "sum"),
        capital_mediano=("capital_social", "median"),
        idade_mediana_anos=("idade_meses", lambda s: (s / 12).median()),
        ceps_distintos=("cep", "nunique"),
    )
    # Percentual de matrizes e participação de cada bairro no município.
    tab["pct_matriz"] = (tab["matrizes"] / tab["estabelecimentos"] * 100).round(2)
    tab["share_municipio_pct"] = (
        tab["estabelecimentos"] / tab["estabelecimentos"].sum() * 100
    ).round(3)
    # Ordena do maior para o menor e calcula a participação acumulada.
    tab = tab.sort_values("estabelecimentos", ascending=False).round(2)
    tab["share_acumulado_pct"] = tab["share_municipio_pct"].cumsum().round(2)
    # Grava o ranking de bairros.
    tab.to_csv(SAIDA / "D1_ranking_bairros.csv")

    # Gráfico: os 25 bairros com mais estabelecimentos.
    top = tab.head(25)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(top.index, top["estabelecimentos"])
    ax.invert_yaxis()
    ax.set_xlabel("Estabelecimentos ativos")
    ax.set_title("Vinte e cinco bairros com maior concentracao empresarial")
    plt.tight_layout()
    plt.savefig(SAIDA / "GD1_ranking_bairros.png")
    plt.close()

    # D1b: índice de Gini, que mede o quanto os estabelecimentos se
    # concentram em poucos bairros (0 = distribuição igual; 1 = tudo em um).
    integrar = np.trapezoid if hasattr(np, "trapezoid") else np.trapz  # NumPy 2.x

    # Calcula o índice a partir da curva de Lorenz.
    def _gini(valores: np.ndarray) -> float:
        v = np.sort(np.asarray(valores, dtype=float))
        acum = np.cumsum(v) / v.sum()
        eixo = np.arange(1, len(v) + 1) / len(v)
        return float(1 - 2 * integrar(acum, eixo))

    # Calcula o índice com três cortes de bairro, como teste de sensibilidade.
    # O corte principal é o de 300 estabelecimentos; os outros dois mostram
    # como a variação de grafia do bairro distorce o resultado.
    n = tab["estabelecimentos"]
    cortes = {
        "todos_os_rotulos": n,
        "min_50_estabelecimentos": n[n >= 50],
        f"min_{MINIMO_BAIRRO}_estabelecimentos": n[n >= MINIMO_BAIRRO],
    }
    linhas = []
    for rotulo, serie in cortes.items():
        linhas.append({
            "corte": rotulo,
            "bairros_considerados": int(len(serie)),
            "estabelecimentos_cobertos": int(serie.sum()),
            "cobertura_pct": round(100 * serie.sum() / n.sum(), 3),
            "gini_locacional": round(_gini(serie.values), 4),
            "principal": rotulo.startswith(f"min_{MINIMO_BAIRRO}"),
        })
    # Grava o índice de cada corte.
    pd.DataFrame(linhas).to_csv(SAIDA / "D1b_gini_locacional.csv", index=False)

    # Gráfico: curva de Lorenz dos três cortes (o principal em destaque).
    fig, ax = plt.subplots(figsize=(5.5, 5))
    for rotulo, serie in cortes.items():
        v = np.sort(serie.values.astype(float))
        acum = np.cumsum(v) / v.sum()
        eixo = np.arange(1, len(v) + 1) / len(v)
        principal = rotulo.startswith(f"min_{MINIMO_BAIRRO}")
        ax.plot(eixo, acum, lw=2.2 if principal else 1.2,
                ls="-" if principal else ":",
                label=f"{rotulo} (n={len(v)}, Gini={_gini(v):.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="gray", label="Equidistribuicao")
    ax.set_xlabel("Proporcao acumulada de bairros")
    ax.set_ylabel("Proporcao acumulada de estabelecimentos")
    ax.set_title("Curva de Lorenz da distribuicao territorial")
    ax.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(SAIDA / "GD1b_lorenz_bairros.png")
    plt.close()
    return tab


# ========================================================================
# D2 - ESPECIALIZAÇÃO DOS BAIRROS (QUOCIENTE LOCACIONAL)
# ========================================================================
#
# Compara o peso de um setor no bairro com o peso desse setor no município.
# Acima de 1: o bairro é mais especializado naquele setor que a média.
# Acima de 1,25: especialização considerada relevante.
def d2_quociente_locacional(ativos: pd.DataFrame,
                            minimo_bairro: int = MINIMO_BAIRRO) -> pd.DataFrame:
    # Conta estabelecimentos por bairro e setor, só nos bairros acima do corte.
    tabela = pd.crosstab(ativos["bairro_norm"], ativos["secao_desc"])
    tabela = tabela[tabela.sum(axis=1) >= minimo_bairro]

    # Calcula quanto cada bairro teria se seguisse a média do município.
    total = tabela.values.sum()
    share_bairro = tabela.sum(axis=1) / total
    share_secao = tabela.sum(axis=0) / total
    esperado = np.outer(share_bairro, share_secao) * total

    # Quociente: valor real dividido pelo esperado.
    ql = pd.DataFrame(tabela.values / np.where(esperado == 0, np.nan, esperado),
                      index=tabela.index, columns=tabela.columns).round(3)
    ql.to_csv(SAIDA / "D2a_quociente_locacional.csv")

    # Lista as especializações relevantes (acima de 1,25 e com 50+ estabelecimentos).
    longo = (ql.stack().rename("ql").reset_index()
             .merge(tabela.stack().rename("estabelecimentos").reset_index(),
                    on=["bairro_norm", "secao_desc"]))
    longo = longo[(longo["ql"] >= 1.25) & (longo["estabelecimentos"] >= 50)]
    longo = longo.sort_values("ql", ascending=False)
    longo.to_csv(SAIDA / "D2b_especializacoes_locais.csv", index=False)

    # Gráfico: mapa de calor dos 20 maiores bairros.
    principais = ql.loc[tabela.sum(axis=1).nlargest(20).index]
    fig, ax = plt.subplots(figsize=(11, 7))
    im = ax.imshow(principais.values, aspect="auto", cmap="RdYlBu_r",
                   vmin=0, vmax=3)
    ax.set_xticks(range(len(principais.columns)))
    ax.set_xticklabels(principais.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(principais.index)))
    ax.set_yticklabels(principais.index, fontsize=7)
    ax.set_title("Quociente Locacional por bairro e secao CNAE")
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="QL")
    plt.tight_layout()
    plt.savefig(SAIDA / "GD2_mapa_calor_ql.png")
    plt.close()
    return ql


# ========================================================================
# D3 - CONCENTRAÇÃO DE CADA SETOR NO TERRITÓRIO
# ========================================================================
#
# Mede se um setor se aglomera em poucos bairros ou se espalha pelo
# município, e aponta o bairro principal de cada setor.
def d3_concentracao_espacial(ativos: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for secao, grupo in ativos.groupby("secao_desc"):
        # Para cada setor: participação de cada bairro.
        share = grupo["bairro_norm"].value_counts(normalize=True)
        if share.size == 0:
            continue
        linhas.append({
            "secao_desc": secao,
            "estabelecimentos": int(len(grupo)),
            "bairros_ocupados": int(share.size),
            # Índice de concentração e peso dos 3 maiores bairros.
            "hhi_locacional": round(float((share ** 2).sum() * 10_000), 1),
            "share_top3_bairros_pct": round(float(share.head(3).sum() * 100), 2),
            "bairro_principal": share.index[0],
        })
    tab = (pd.DataFrame(linhas)
           .sort_values("hhi_locacional", ascending=False))
    # Grava a tabela.
    tab.to_csv(SAIDA / "D3_concentracao_espacial.csv", index=False)
    return tab


# ========================================================================
# D4 - MATRIZES E FILIAIS POR SETOR
# ========================================================================
def d4_matriz_filial(ativos: pd.DataFrame) -> pd.DataFrame:
    tab = ativos.groupby("secao_desc").agg(
        estabelecimentos=("cnpj_completo", "count"),
        matrizes=("e_matriz", "sum"),
    )
    # Conta filiais e calcula o percentual de filiais em cada setor.
    tab["filiais"] = tab["estabelecimentos"] - tab["matrizes"]
    tab["pct_filial"] = (tab["filiais"] / tab["estabelecimentos"] * 100).round(2)
    tab = tab.sort_values("pct_filial", ascending=False)
    # Grava a tabela.
    tab.to_csv(SAIDA / "D4_matriz_filial.csv")
    return tab


# ========================================================================
# D5 - ALCANCE GEOGRÁFICO DAS EMPRESAS SEDIADAS NO MUNICÍPIO
# ========================================================================
#
# Para cada empresa com matriz no município, conta suas unidades ativas no
# país e em quantos estados elas estão.
# Observação: como quase todas as empresas têm uma única unidade, a mediana
# do índice é a mesma em todos os setores e não serve para compará-los.
# A comparação usa o percentual de empresas em mais de um estado.
def d5_alcance(ativos: pd.DataFrame) -> pd.DataFrame:
    # Lê a rede nacional e mantém só as unidades ativas.
    rede = pd.read_parquet(cfg.DIR_BASE / "rede_nacional.parquet")
    rede = rede[rede["situacao_cadastral"] == "02"]

    # Para cada empresa: unidades, estados e municípios atingidos.
    perfil = rede.groupby("cnpj_basico").agg(
        unidades=("uf", "size"),
        ufs_atingidas=("uf", "nunique"),
        municipios_atingidos=("municipio", "nunique"),
    )
    # Unidades fora do estado do Rio de Janeiro.
    perfil["unidades_fora_uf_sede"] = perfil["unidades"] - (
        rede[rede["uf"] == cfg.UF_ALVO].groupby("cnpj_basico").size()
        .reindex(perfil.index).fillna(0)
    )
    # Índice de alcance: combina número de unidades e número de estados.
    perfil["indice_alcance"] = (
        np.log1p(perfil["unidades"]) * (1 + perfil["ufs_atingidas"])
    ).round(3)

    # Acrescenta dados da empresa (setor, bairro, capital, porte).
    contexto = (ativos[ativos["e_matriz"]]
                .drop_duplicates("cnpj_basico")
                .set_index("cnpj_basico")[
                    ["razao_social", "secao_desc", "elo_cadeia", "orientacao",
                     "bairro_norm", "capital_social", "porte_empresa"]])
    perfil = perfil.join(contexto, how="inner")
    perfil = perfil.sort_values("indice_alcance", ascending=False)
    # Grava o resultado por empresa.
    perfil.to_csv(SAIDA / "D5a_alcance_por_empresa.csv")

    # Resume por setor: médias, máximos, percentual em mais de um estado
    # e percentis altos do índice.
    resumo = perfil.groupby("secao_desc").agg(
        empresas=("unidades", "size"),
        unidades_medias=("unidades", "mean"),
        unidades_max=("unidades", "max"),
        ufs_medias=("ufs_atingidas", "mean"),
        pct_multiunidade=("unidades", lambda s: (s > 1).mean() * 100),
        pct_interestadual=("ufs_atingidas", lambda s: (s > 1).mean() * 100),
        indice_alcance_mediano=("indice_alcance", "median"),
        indice_alcance_p90=("indice_alcance", lambda s: s.quantile(.90)),
        indice_alcance_p99=("indice_alcance", lambda s: s.quantile(.99)),
        indice_alcance_max=("indice_alcance", "max"),
    ).round(2).sort_values("pct_interestadual", ascending=False)
    # Grava o resumo por setor.
    resumo.to_csv(SAIDA / "D5b_alcance_por_secao.csv")

    # Grava uma nota explicando por que a mediana do índice não discrimina os setores.
    pd.DataFrame([{
        "empresas_com_matriz_ativa": int(len(perfil)),
        "pct_com_uma_unidade": round(float((perfil["unidades"] == 1).mean() * 100), 2),
        "pct_com_uma_uf": round(float((perfil["ufs_atingidas"] == 1).mean() * 100), 2),
        "mediana_unidades": float(perfil["unidades"].median()),
        "p99_unidades": float(perfil["unidades"].quantile(.99)),
        "max_unidades": int(perfil["unidades"].max()),
        "indice_alcance_mediano_global": round(float(perfil["indice_alcance"].median()), 4),
        "nota": ("mediana do indice e constante (ln(2)*2) em todas as secoes; "
                 "usar pct_interestadual, unidades_medias e percentis altos"),
    }]).to_csv(SAIDA / "D5c_nota_sobre_a_mediana.csv", index=False)

    # Gráfico: percentual de empresas presentes em mais de um estado.
    rel = resumo[resumo["empresas"] >= 100].head(15)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(rel.index, rel["pct_interestadual"])
    ax.invert_yaxis()
    ax.set_xlabel("Empresas com unidades em mais de uma UF (%)")
    ax.set_title("Alcance interestadual das redes com sede no municipio")
    plt.tight_layout()
    plt.savefig(SAIDA / "GD5_alcance_interestadual.png")
    plt.close()
    return resumo


# ========================================================================
# D6 - LOGÍSTICA POR BAIRRO
# ========================================================================
#
# Quantidade de estabelecimentos de transporte, armazenagem e entregas em
# cada bairro, e o peso deles no total do bairro.
def d6_logistica(ativos: pd.DataFrame) -> pd.DataFrame:
    # Separa os estabelecimentos das divisões de logística (s01_config.py).
    log = ativos[ativos["divisao"].isin(cfg.DIVISOES_LOGISTICA)]
    tab = log.groupby("bairro_norm").agg(
        estabelecimentos_logisticos=("cnpj_completo", "count"),
        capital_mediano=("capital_social", "median"),
    )
    # Junta com o total do bairro e calcula o peso da logística.
    total_bairro = ativos.groupby("bairro_norm").size().rename("total_bairro")
    tab = tab.join(total_bairro)
    tab["intensidade_logistica_pct"] = (
        tab["estabelecimentos_logisticos"] / tab["total_bairro"] * 100
    ).round(2)
    tab = tab.sort_values("estabelecimentos_logisticos",
                          ascending=False).round(2)
    # Ordena e grava a tabela.
    tab.to_csv(SAIDA / "D6_logistica_por_bairro.csv")
    return tab


# ========================================================================
# EXECUÇÃO
# ========================================================================
#
# Lê os dados, separa os ativos e calcula os indicadores em ordem.
def main() -> None:
    print("=== PESQUISA 2 | DISTRIBUICAO FISICA ===\n")
    df = carregar()
    # Separa os ativos e informa quantos ficaram sem bairro.
    ativos = df[df["ativa"]].copy()
    nao_informado = (ativos["bairro_norm"] == "NAO INFORMADO").mean() * 100
    print(f"Ativos: {len(ativos):,} | Bairro nao informado: {nao_informado:.2f}%\n")

    # Calcula e mostra cada indicador.
    print("D1 - Ranking de bairros");        print(d1_bairros(ativos).head(10), "\n")
    print("D2 - Quociente Locacional");      d2_quociente_locacional(ativos); print("ok\n")
    print("D3 - Concentracao espacial");     print(d3_concentracao_espacial(ativos).head(10), "\n")
    print("D4 - Matriz e filial");           print(d4_matriz_filial(ativos).head(10), "\n")
    print("D5 - Alcance geografico");        print(d5_alcance(ativos).head(10), "\n")
    print("D6 - Infraestrutura logistica");  print(d6_logistica(ativos).head(10), "\n")

    print(f"[fim] Resultados em {SAIDA}")


# Ponto de partida quando o script é executado.
if __name__ == "__main__":
    main()

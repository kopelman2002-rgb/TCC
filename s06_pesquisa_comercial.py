"""
6. s06_pesquisa_comercial.py
============================
Pesquisa 1 - Dimensão comercial.

Pergunta: como se distribuem os públicos de compra e venda (empresas,
consumidor final, governo) e as posições na cadeia de suprimentos entre
as empresas do município, e que desequilíbrios esse arranjo revela?

Indicadores produzidos:
  I1  Composição das empresas por posição na cadeia e público-alvo
  I2  Relação entre oferta e demanda potencial em cada posição da cadeia
  I3  Concentração das atividades dentro de cada setor (índice HHI)
  I4  Perfil de porte e capital por público-alvo
  I5  Ranking das atividades econômicas mais frequentes
  I6  Taxa de encerramento cadastral por posição na cadeia

Usa só estabelecimentos ativos, exceto o I6, que usa todos os registros.

Saídas (tabelas e gráficos): saidas/pesquisa_1_comercial/

Como rodar:
    python s06_pesquisa_comercial.py
"""

# Bibliotecas usadas pelo script.
from __future__ import annotations

import matplotlib
# Gera os gráficos direto em arquivo, sem abrir janela.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configurações do projeto (pastas, códigos e classificação CNAE).
import s01_config as cfg

# Pasta onde os resultados desta pesquisa são gravados.
SAIDA = cfg.DIR_SAIDAS / "pesquisa_1_comercial"
SAIDA.mkdir(parents=True, exist_ok=True)

# Aparência padrão dos gráficos.
plt.rcParams.update({"figure.dpi": 160, "font.size": 9,
                     "axes.grid": True, "grid.alpha": 0.3})


# ========================================================================
# LEITURA DOS DADOS
# ========================================================================
#
# Lê a base e classifica cada estabelecimento pela tabela CNAE do s01_config.py.
def carregar() -> pd.DataFrame:
    # Lê a base analítica.
    df = pd.read_parquet(cfg.DIR_BASE / "base_analitica.parquet")

    # Classifica cada atividade: seção, posição na cadeia e público-alvo.
    classes = df["cnae_fiscal_principal"].apply(cfg.classificar_cnae)
    df[["secao", "divisao", "divisao_desc", "elo_cadeia", "orientacao"]] = (
        pd.DataFrame(classes.tolist(), index=df.index)
    )
    # Acrescenta as descrições por extenso (seção, situação e porte).
    df["secao_desc"] = df["secao"].map(cfg.NOMES_SECAO).fillna("Nao classificado")
    df["situacao_desc"] = df["situacao_cadastral"].map(cfg.SITUACAO_CADASTRAL)
    df["porte_desc"] = df["porte_empresa"].map(cfg.PORTE_EMPRESA)
    # Idade da empresa em anos.
    df["idade_anos"] = df["idade_meses"] / 12.0
    # Marca os estabelecimentos ativos.
    df["ativa"] = df["situacao_cadastral"].eq("02")
    return df


# ========================================================================
# I1 - COMPOSIÇÃO POR POSIÇÃO NA CADEIA E PÚBLICO-ALVO
# ========================================================================
def i1_composicao(ativos: pd.DataFrame) -> pd.DataFrame:
    # Conta os estabelecimentos em cada combinação de posição e público.
    tab = (ativos.pivot_table(index="elo_cadeia", columns="orientacao",
                              values="cnpj_completo", aggfunc="count",
                              fill_value=0, margins=True, margins_name="Total"))
    # Converte as contagens em percentual do total.
    pct = (tab / tab.loc["Total", "Total"] * 100).round(2)
    # Grava as tabelas em número e em percentual.
    tab.to_csv(SAIDA / "I1a_composicao_absoluta.csv")
    pct.to_csv(SAIDA / "I1b_composicao_percentual.csv")

    # Gráfico: barras empilhadas por posição na cadeia.
    plot = tab.drop(index="Total", columns="Total")
    plot = plot.loc[plot.sum(axis=1).sort_values(ascending=False).index]
    ax = plot.plot(kind="barh", stacked=True, figsize=(8, 4.5))
    ax.set_xlabel("Estabelecimentos ativos")
    ax.set_ylabel("")
    ax.set_title("Composicao do tecido empresarial por elo da cadeia e publico-alvo")
    ax.legend(title="Orientacao", fontsize=8)
    plt.tight_layout()
    plt.savefig(SAIDA / "G1_composicao_elo_publico.png")
    plt.close()
    return tab


# ========================================================================
# I2 - OFERTA E DEMANDA POTENCIAL
# ========================================================================
#
# Compara quantos estabelecimentos vendem para empresas (ofertantes) com
# quantos vendem para consumidor ou governo (demandantes), em cada posição.
# Em três posições não há demandantes, e a relação fica indefinida; a
# tabela informa isso na coluna "situacao_indicador".
def i2_oferta_demanda(ativos: pd.DataFrame) -> pd.DataFrame:
    # Separa os ofertantes (público B2B ou misto).
    ofertantes = ativos[ativos["orientacao"].isin(["B2B", "MISTO"])]
    # Conta ofertantes e total por posição na cadeia.
    n_ofertantes = ofertantes.groupby("elo_cadeia").size()
    n_total = ativos.groupby("elo_cadeia").size()

    # Monta a tabela com as duas contagens.
    tab = pd.DataFrame({
        "estabelecimentos": n_total,
        "ofertantes_b2b": n_ofertantes,
    }).fillna(0)
    # Demandantes: o que sobra depois de tirar os ofertantes.
    tab["demandantes_b2c_b2g"] = tab["estabelecimentos"] - tab["ofertantes_b2b"]
    # Relação ofertantes / demandantes (vazia quando não há demandantes).
    tab["razao_oferta_demanda"] = (
        tab["ofertantes_b2b"] / tab["demandantes_b2c_b2g"].replace(0, np.nan)
    ).round(3)

    # Indica se a relação é válida, pede cautela ou é indefinida.
    tab["situacao_indicador"] = np.where(
        tab["demandantes_b2c_b2g"] == 0,
        "indefinido: elo sem divisoes CNAE B2C/B2G",
        np.where(tab["demandantes_b2c_b2g"] < 0.05 * tab["estabelecimentos"],
                 "cautela: denominador < 5% do elo",
                 "definido"),
    )

    # Leitura alternativa: ofertantes sobre o total de empresas do município.
    tab["razao_vs_tecido_total"] = (
        tab["ofertantes_b2b"] / len(ativos)
    ).round(5)

    # Peso de cada posição no total de estabelecimentos.
    tab["participacao_pct"] = (
        tab["estabelecimentos"] / tab["estabelecimentos"].sum() * 100
    ).round(2)
    tab = tab.sort_values("estabelecimentos", ascending=False)
    # Ordena e grava a tabela.
    tab.to_csv(SAIDA / "I2_razao_oferta_demanda.csv")
    return tab


# ========================================================================
# I3 - CONCENTRAÇÃO DAS ATIVIDADES DENTRO DE CADA SETOR (HHI)
# ========================================================================
#
# Mede se cada setor é dominado por poucas atividades ou dividido entre
# muitas. Abaixo de 1.500: desconcentrado; de 1.500 a 2.500: moderado;
# acima de 2.500: altamente concentrado.
def i3_hhi(ativos: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    # Calcula o índice setor por setor.
    for secao, grupo in ativos.groupby("secao"):
        # Participação de cada atividade dentro do setor.
        share = grupo["cnae_fiscal_principal"].value_counts(normalize=True)
        # Índice: soma dos quadrados das participações.
        hhi = float((share ** 2).sum() * 10_000)
        # Guarda o resultado do setor e sua atividade dominante.
        linhas.append({
            "secao": secao,
            "secao_desc": cfg.NOMES_SECAO.get(secao, "Nao classificado"),
            "estabelecimentos": int(len(grupo)),
            "cnaes_distintos": int(share.size),
            "hhi": round(hhi, 1),
            "cnae_dominante": share.index[0] if share.size else None,
            "share_dominante_pct": round(float(share.iloc[0] * 100), 2) if share.size else None,
        })
    tab = pd.DataFrame(linhas).sort_values("estabelecimentos", ascending=False)
    # Classifica cada setor nas faixas de concentração.
    tab["classificacao"] = pd.cut(
        tab["hhi"], bins=[-1, 1500, 2500, 10_001],
        labels=["Desconcentrado", "Moderadamente concentrado", "Altamente concentrado"],
    )
    tab.to_csv(SAIDA / "I3_hhi_por_secao.csv", index=False)

    # Gráfico: índice por setor, com as linhas das faixas.
    rel = tab[tab["estabelecimentos"] >= 200].head(15)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(rel["secao_desc"], rel["hhi"])
    ax.axvline(1500, ls="--", lw=1, color="gray")
    ax.axvline(2500, ls="--", lw=1, color="gray")
    ax.set_xlabel("HHI (pontos)")
    ax.set_title("Concentracao intrassetorial por secao CNAE")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(SAIDA / "G3_hhi_por_secao.png")
    plt.close()
    return tab


# ========================================================================
# I4 - PERFIL POR PÚBLICO-ALVO
# ========================================================================
#
# Para cada público-alvo: percentual de microempresas, MEI e Simples,
# capital social, idade e quantidade de atividades secundárias.
def i4_perfil(ativos: pd.DataFrame) -> pd.DataFrame:
    tab = ativos.groupby("orientacao").agg(
        estabelecimentos=("cnpj_completo", "count"),
        pct_microempresa=("porte_desc", lambda s: (s == "Microempresa").mean() * 100),
        pct_mei=("opcao_mei", lambda s: (s == "S").mean() * 100),
        pct_simples=("opcao_simples", lambda s: (s == "S").mean() * 100),
        capital_mediano=("capital_social", "median"),
        capital_p90=("capital_social", lambda s: s.quantile(0.90)),
        idade_mediana_anos=("idade_anos", "median"),
        cnaes_secundarios_medio=("qtd_cnae_secundario", "mean"),
    ).round(2).sort_values("estabelecimentos", ascending=False)
    # Grava a tabela.
    tab.to_csv(SAIDA / "I4_perfil_por_orientacao.csv")
    return tab


# ========================================================================
# I5 - RANKING DAS ATIVIDADES MAIS FREQUENTES
# ========================================================================
def i5_top_atividades(ativos: pd.DataFrame) -> pd.DataFrame:
    # Conta os estabelecimentos de cada atividade, com capital, idade e filiais.
    tab = (ativos.groupby(["cnae_fiscal_principal", "cnae_desc",
                           "elo_cadeia", "orientacao"])
           .agg(estabelecimentos=("cnpj_completo", "count"),
                capital_mediano=("capital_social", "median"),
                idade_mediana=("idade_anos", "median"),
                pct_filial=("identificador_matriz_filial",
                            lambda s: (s == "2").mean() * 100))
           .round(2)
           .reset_index()
           .sort_values("estabelecimentos", ascending=False))
    # Participação de cada atividade e participação acumulada.
    tab["share_pct"] = (tab["estabelecimentos"] /
                        tab["estabelecimentos"].sum() * 100).round(3)
    tab["share_acumulado_pct"] = tab["share_pct"].cumsum().round(2)
    # Grava a tabela.
    tab.to_csv(SAIDA / "I5_ranking_cnae.csv", index=False)

    # Gráfico: as 20 atividades mais frequentes.
    top = tab.head(20)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["cnae_desc"].str.slice(0, 60), top["estabelecimentos"])
    ax.invert_yaxis()
    ax.set_xlabel("Estabelecimentos ativos")
    ax.set_title("Vinte atividades economicas mais frequentes")
    plt.tight_layout()
    plt.savefig(SAIDA / "G5_top20_cnae.png")
    plt.close()
    return tab


# ========================================================================
# I6 - ENCERRAMENTO CADASTRAL
# ========================================================================
#
# Percentual de registros baixados ou inaptos em cada posição da cadeia e
# público-alvo. Usa todos os registros, não só os ativos.
def i6_descontinuidade(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Marca os registros baixados ou inaptos.
    df["baixada_inapta"] = df["situacao_cadastral"].isin(["08", "04"])

    # Conta registros, ativos e encerrados em cada combinação.
    tab = df.groupby(["elo_cadeia", "orientacao"]).agg(
        registros=("cnpj_completo", "count"),
        ativos=("ativa", "sum"),
        baixados_ou_inaptos=("baixada_inapta", "sum"),
    )
    # Separa os inativos em: encerrados e nulos/suspensos.
    tab["nao_ativos"] = tab["registros"] - tab["ativos"]
    tab["nulas_ou_suspensas"] = tab["nao_ativos"] - tab["baixados_ou_inaptos"]
    # Taxa principal: baixados e inaptos sobre o total.
    tab["taxa_descontinuidade_pct"] = (
        tab["baixados_ou_inaptos"] / tab["registros"] * 100
    ).round(2)
    # Taxa complementar: todos os não ativos sobre o total.
    tab["taxa_nao_ativos_pct"] = (
        tab["nao_ativos"] / tab["registros"] * 100
    ).round(2)
    tab = tab.sort_values("taxa_descontinuidade_pct", ascending=False)
    # Ordena e grava a tabela.
    tab.to_csv(SAIDA / "I6_descontinuidade.csv")
    return tab


# ========================================================================
# EXECUÇÃO
# ========================================================================
#
# Lê os dados, separa os ativos e calcula os seis indicadores em ordem.
def main() -> None:
    print("=== PESQUISA 1 | DIMENSAO COMERCIAL ===\n")
    df = carregar()
    # Separa os estabelecimentos ativos.
    ativos = df[df["ativa"]].copy()
    print(f"Registros totais: {len(df):,} | Ativos: {len(ativos):,}\n")

    # Calcula e mostra cada indicador (o I6 usa todos os registros).
    print("I1 - Composicao por elo e publico");      print(i1_composicao(ativos), "\n")
    print("I2 - Razao oferta/demanda");              print(i2_oferta_demanda(ativos), "\n")
    print("I3 - Concentracao (HHI)");                print(i3_hhi(ativos).head(10), "\n")
    print("I4 - Perfil por orientacao");             print(i4_perfil(ativos), "\n")
    print("I5 - Ranking de atividades");             print(i5_top_atividades(ativos).head(10), "\n")
    print("I6 - Descontinuidade cadastral");         print(i6_descontinuidade(df).head(10), "\n")

    print(f"[fim] Resultados em {SAIDA}")


# Ponto de partida quando o script é executado.
if __name__ == "__main__":
    main()

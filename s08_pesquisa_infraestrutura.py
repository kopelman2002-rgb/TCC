"""
8. s08_pesquisa_infraestrutura.py
=================================
Pesquisa 3 - Infraestrutura e capacidade instalada.

Pergunta: que perfis de capacidade instalada podem ser inferidos a partir
das informações do cadastro, e como eles variam entre setores?

Atenção: o cadastro não traz faturamento, patrimônio, imobilizado nem
número de empregados. Por isso a pesquisa usa aproximações:
  capital social declarado    -> aporte de recursos na abertura
  porte e Simples/MEI         -> escala de faturamento
  número de unidades          -> estrutura física
  atividades secundárias      -> amplitude de atuação
  quadro de sócios            -> estrutura de capital
  idade da empresa            -> maturidade
Os resultados descrevem o cadastro, não a contabilidade das empresas.

Indicadores produzidos:
  E1  Capital social por porte e por natureza jurídica
  E2  Quadro de sócios
  E3  Amplitude de atuação e número de unidades
  E4  Opção pelo Simples Nacional e MEI por setor
  E5  Índice Composto de Capacidade Instalada (ICCI)
  E6  Perfis de empresa por agrupamento

Usa só estabelecimentos ativos.

Saídas (tabelas e gráficos): saidas/pesquisa_3_infraestrutura/

Como rodar:
    python s08_pesquisa_infraestrutura.py
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
SAIDA = cfg.DIR_SAIDAS / "pesquisa_3_infraestrutura"
SAIDA.mkdir(parents=True, exist_ok=True)

# Aparência padrão dos gráficos.
plt.rcParams.update({"figure.dpi": 160, "font.size": 9,
                     "axes.grid": True, "grid.alpha": 0.3})


# ========================================================================
# LEITURA DOS DADOS
# ========================================================================
#
# Lê a base e a tabela de sócios.
def carregar() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Lê a base analítica e os sócios.
    df = pd.read_parquet(cfg.DIR_BASE / "base_analitica.parquet")
    socios = pd.read_parquet(cfg.DIR_BASE / "socios.parquet")

    # Classifica cada atividade pela tabela CNAE do s01_config.py.
    classes = df["cnae_fiscal_principal"].apply(cfg.classificar_cnae)
    df[["secao", "divisao", "divisao_desc", "elo_cadeia", "orientacao"]] = (
        pd.DataFrame(classes.tolist(), index=df.index)
    )
    # Acrescenta descrições, idade em anos e marca ativos e matrizes.
    df["secao_desc"] = df["secao"].map(cfg.NOMES_SECAO).fillna("Nao classificado")
    df["porte_desc"] = df["porte_empresa"].map(cfg.PORTE_EMPRESA).fillna("Nao informado")
    df["idade_anos"] = (df["idade_meses"] / 12).round(2)
    df["ativa"] = df["situacao_cadastral"].eq("02")
    df["e_matriz"] = df["identificador_matriz_filial"].eq("1")

    # Traduz tipo e faixa etária dos sócios.
    socios["tipo_socio"] = socios["identificador_socio"].map(cfg.IDENTIFICADOR_SOCIO)
    socios["faixa_etaria_desc"] = socios["faixa_etaria"].map(cfg.FAIXA_ETARIA_SOCIO)
    return df, socios


# ========================================================================
# E1 - CAPITAL SOCIAL
# ========================================================================
def e1_capital(ativos: pd.DataFrame) -> pd.DataFrame:
    # Considera uma linha por empresa (a matriz).
    empresas = ativos[ativos["e_matriz"]].drop_duplicates("cnpj_basico")

    # Distribuição do capital por porte: mínimo, quartis, mediana, média.
    por_porte = empresas.groupby("porte_desc")["capital_social"].agg(
        empresas="count", minimo="min", q25=lambda s: s.quantile(.25),
        mediana="median", q75=lambda s: s.quantile(.75),
        p95=lambda s: s.quantile(.95), media="mean",
    ).round(2)
    por_porte.to_csv(SAIDA / "E1a_capital_por_porte.csv")

    # Capital e idade por natureza jurídica (25 mais comuns).
    por_natureza = (empresas.groupby("natureza_desc")
                    .agg(empresas=("cnpj_basico", "count"),
                         capital_mediano=("capital_social", "median"),
                         capital_p90=("capital_social", lambda s: s.quantile(.90)),
                         idade_mediana=("idade_anos", "median"))
                    .round(2)
                    .sort_values("empresas", ascending=False)
                    .head(25))
    por_natureza.to_csv(SAIDA / "E1b_capital_por_natureza.csv")

    # Gráfico: dispersão do capital por porte, em escala logarítmica.
    dados = empresas[empresas["capital_social"] > 0].copy()
    dados["log_capital"] = np.log10(dados["capital_social"])
    ordem = [p for p in ["Microempresa", "Empresa de pequeno porte",
                         "Demais", "Nao informado"]
             if p in dados["porte_desc"].unique()]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.boxplot([dados.loc[dados["porte_desc"] == p, "log_capital"].dropna()
                for p in ordem], showfliers=False)
    ax.set_xticks(range(1, len(ordem) + 1))
    ax.set_xticklabels(ordem)
    ax.set_ylabel("log10 do capital social declarado (R$)")
    ax.set_title("Dispersao do capital social por porte empresarial")
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(SAIDA / "GE1_capital_por_porte.png")
    plt.close()
    return por_porte


# ========================================================================
# E2 - QUADRO DE SÓCIOS
# ========================================================================
def e2_societario(ativos: pd.DataFrame, socios: pd.DataFrame) -> pd.DataFrame:
    # Para cada empresa: número de sócios, sócios empresa e estrangeiros.
    perfil = socios.groupby("cnpj_basico").agg(
        qtd_socios=("qualificacao_socio", "size"),
        socios_pj=("tipo_socio", lambda s: (s == "Pessoa juridica").sum()),
        socios_estrangeiros=("tipo_socio", lambda s: (s == "Estrangeiro").sum()),
        entrada_mais_antiga=("data_entrada", "min"),
    )
    perfil["pct_socios_pj"] = (perfil["socios_pj"] /
                               perfil["qtd_socios"] * 100).round(2)
    # Grava o perfil por empresa.
    perfil.to_csv(SAIDA / "E2a_perfil_societario_empresa.csv")

    matrizes = ativos[ativos["e_matriz"]].drop_duplicates("cnpj_basico")
    # Junta com as empresas ativas e calcula o capital por sócio.
    juncao = matrizes.set_index("cnpj_basico").join(perfil, how="left")
    juncao["qtd_socios"] = juncao["qtd_socios"].fillna(0)
    juncao["capital_por_socio"] = (
        juncao["capital_social"] / juncao["qtd_socios"].replace(0, np.nan)
    ).round(2)

    # Resume por setor: sócio único, sócio empresa, estrangeiro, capital por sócio.
    resumo = juncao.groupby("secao_desc").agg(
        empresas=("qtd_socios", "size"),
        socios_medio=("qtd_socios", "mean"),
        pct_socio_unico=("qtd_socios", lambda s: (s <= 1).mean() * 100),
        pct_com_socio_pj=("socios_pj", lambda s: (s.fillna(0) > 0).mean() * 100),
        pct_com_estrangeiro=("socios_estrangeiros",
                             lambda s: (s.fillna(0) > 0).mean() * 100),
        capital_por_socio_mediano=("capital_por_socio", "median"),
    ).round(2).sort_values("empresas", ascending=False)
    resumo.to_csv(SAIDA / "E2b_societario_por_secao.csv")

    # Distribuição dos sócios por faixa etária.
    faixas = (socios["faixa_etaria_desc"].value_counts(normalize=True) * 100).round(2)
    faixas.rename("percentual").to_csv(SAIDA / "E2c_faixa_etaria_socios.csv")
    return resumo


# ========================================================================
# E3 - AMPLITUDE DE ATUAÇÃO E NÚMERO DE UNIDADES
# ========================================================================
def e3_escopo(ativos: pd.DataFrame) -> pd.DataFrame:
    # Conta as unidades de cada empresa no município.
    unidades = ativos.groupby("cnpj_basico").size().rename("unidades_no_municipio")
    matrizes = (ativos[ativos["e_matriz"]]
                .drop_duplicates("cnpj_basico")
                .set_index("cnpj_basico")
                .join(unidades))

    # Por setor: atividades secundárias, empresas com 3 ou mais,
    # unidades, empresas com mais de uma unidade e idade.
    tab = matrizes.groupby("secao_desc").agg(
        empresas=("unidades_no_municipio", "size"),
        cnaes_secundarios_medio=("qtd_cnae_secundario", "mean"),
        pct_com_escopo_ampliado=("qtd_cnae_secundario",
                                 lambda s: (s >= 3).mean() * 100),
        unidades_medias=("unidades_no_municipio", "mean"),
        pct_multiunidade=("unidades_no_municipio",
                          lambda s: (s > 1).mean() * 100),
        idade_mediana=("idade_anos", "median"),
    ).round(2).sort_values("cnaes_secundarios_medio", ascending=False)
    # Grava a tabela.
    tab.to_csv(SAIDA / "E3_escopo_operacional.csv")
    return tab


# ========================================================================
# E4 - SIMPLES NACIONAL E MEI POR SETOR
# ========================================================================
def e4_tributario(ativos: pd.DataFrame) -> pd.DataFrame:
    tab = ativos.groupby("secao_desc").agg(
        estabelecimentos=("cnpj_completo", "count"),
        # Percentual de optantes pelo Simples e pelo MEI, e capital mediano.
        pct_simples=("opcao_simples", lambda s: (s == "S").mean() * 100),
        pct_mei=("opcao_mei", lambda s: (s == "S").mean() * 100),
        capital_mediano=("capital_social", "median"),
    ).round(2).sort_values("pct_mei", ascending=False)
    # Grava a tabela.
    tab.to_csv(SAIDA / "E4_enquadramento_tributario.csv")

    # Gráfico: Simples e MEI lado a lado, por setor.
    rel = tab[tab["estabelecimentos"] >= 500]
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(rel))
    ax.barh(y - 0.2, rel["pct_mei"], height=0.4, label="MEI")
    ax.barh(y + 0.2, rel["pct_simples"], height=0.4, label="Simples Nacional")
    ax.set_yticks(y)
    ax.set_yticklabels(rel.index, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Percentual de estabelecimentos (%)")
    ax.set_title("Enquadramento tributario por secao economica")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(SAIDA / "GE4_enquadramento.png")
    plt.close()
    return tab


# ========================================================================
# E5 - ÍNDICE COMPOSTO DE CAPACIDADE INSTALADA (ICCI)
# ========================================================================
#
# Combina cinco aproximações em uma nota única por empresa.
# Pesos: capital 30%, unidades 25%, atividades secundárias 15%,
# idade 15% e sócios 15%. Valores extremos são limitados para que
# poucas empresas não dominem o resultado.
def e5_icci(ativos: pd.DataFrame, socios: pd.DataFrame) -> pd.DataFrame:
    # Conta unidades e sócios de cada empresa.
    unidades = ativos.groupby("cnpj_basico").size().rename("unidades")
    qtd_socios = socios.groupby("cnpj_basico").size().rename("qtd_socios")

    # Monta uma linha por empresa com essas informações.
    emp = (ativos[ativos["e_matriz"]]
           .drop_duplicates("cnpj_basico")
           .set_index("cnpj_basico")
           .join([unidades, qtd_socios]))
    emp["qtd_socios"] = emp["qtd_socios"].fillna(1)
    # Capital em escala logarítmica, para reduzir o peso dos valores extremos.
    emp["log_capital"] = np.log1p(emp["capital_social"].clip(lower=0))

    # As cinco variáveis do índice e seus pesos.
    componentes = {
        "log_capital": 0.30,
        "unidades": 0.25,
        "qtd_cnae_secundario": 0.15,
        "idade_anos": 0.15,
        "qtd_socios": 0.15,
    }

    escores = pd.DataFrame(index=emp.index)
    # Padroniza cada variável, limita os extremos e aplica o peso.
    for col, peso in componentes.items():
        serie = emp[col].astype(float)
        z = (serie - serie.mean()) / (serie.std(ddof=0) or 1)
        escores[f"z_{col}"] = z.clip(-3, 3)
        escores[f"z_{col}"] *= peso

    # Nota final: soma das cinco partes.
    emp["icci"] = escores.sum(axis=1).round(4)
    # Posição de cada empresa no ranking e faixa de capacidade
    # (muito baixa, baixa, média, alta, muito alta).
    emp["icci_percentil"] = (emp["icci"].rank(pct=True) * 100).round(2)
    emp["estrato_capacidade"] = pd.cut(
        emp["icci_percentil"], bins=[-0.1, 25, 50, 75, 90, 100],
        labels=["Muito baixa", "Baixa", "Media", "Alta", "Muito alta"],
    )

    # Grava o índice por empresa.
    colunas = ["razao_social", "secao_desc", "elo_cadeia", "porte_desc",
               "bairro", "capital_social", "unidades", "qtd_socios",
               "qtd_cnae_secundario", "idade_anos", "icci",
               "icci_percentil", "estrato_capacidade"]
    emp[colunas].sort_values("icci", ascending=False).to_csv(
        SAIDA / "E5a_icci_por_empresa.csv")

    # Resume por setor: índice mediano, percentil 90 e percentual de alta capacidade.
    resumo = emp.groupby("secao_desc").agg(
        empresas=("icci", "size"),
        icci_mediano=("icci", "median"),
        icci_p90=("icci", lambda s: s.quantile(.90)),
        pct_alta_capacidade=("icci_percentil", lambda s: (s >= 75).mean() * 100),
    ).round(3).sort_values("icci_mediano", ascending=False)
    resumo.to_csv(SAIDA / "E5b_icci_por_secao.csv")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    # Gráfico: distribuição do índice entre as empresas.
    ax.hist(emp["icci"].dropna(), bins=80)
    ax.set_xlabel("Indice Composto de Capacidade Instalada")
    ax.set_ylabel("Empresas")
    ax.set_title("Distribuicao do ICCI no municipio")
    plt.tight_layout()
    plt.savefig(SAIDA / "GE5_distribuicao_icci.png")
    plt.close()
    return emp


# ========================================================================
# E6 - PERFIS DE EMPRESA POR AGRUPAMENTO
# ========================================================================
#
# Separa as empresas em 5 grupos parecidos entre si, usando as mesmas
# variáveis do índice e o mesmo tratamento dos valores extremos.
def e6_clusters(emp: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    try:
        # Carrega a ferramenta de agrupamento; se não estiver instalada, pula esta etapa.
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        print("[aviso] scikit-learn nao instalado. Etapa E6 ignorada.")
        return pd.DataFrame()

    # Variáveis usadas no agrupamento; exige amostra mínima.
    cols = ["log_capital", "unidades", "qtd_cnae_secundario",
            "idade_anos", "qtd_socios"]
    dados = emp[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(dados) < k * 10:
        print("[aviso] Amostra insuficiente para agrupamento.")
        return pd.DataFrame()

    # Reduz o peso dos valores extremos (escala logarítmica e limite).
    LOG_COLS = ["unidades", "qtd_socios", "qtd_cnae_secundario"]
    transformado = dados.copy()
    for c in LOG_COLS:
        transformado[c] = np.log1p(transformado[c].clip(lower=0))

    X = StandardScaler().fit_transform(transformado)
    X = np.clip(X, -3, 3)

    # Forma os 5 grupos e marca o grupo de cada empresa.
    modelo = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    dados = dados.assign(cluster=modelo.labels_)

    # Resume cada grupo: médias, medianas, tamanho e participação.
    resumo = dados.groupby("cluster").mean().round(2)
    resumo["empresas"] = dados.groupby("cluster").size()
    resumo["participacao_pct"] = (resumo["empresas"] /
                                  len(dados) * 100).round(2)
    medianas = dados.groupby("cluster")[cols].median().round(2)
    medianas.columns = [f"mediana_{c}" for c in medianas.columns]
    resumo = resumo.join(medianas)
    resumo = resumo.sort_values("empresas", ascending=False)
    # Grava o perfil dos grupos.
    resumo.to_csv(SAIDA / "E6a_perfil_clusters.csv")

    # Avisa se algum grupo ficou com menos de 1% das empresas.
    menor = int(resumo["empresas"].min())
    if menor < 0.01 * len(dados):
        print(f"[aviso] menor cluster tem {menor:,} empresas "
              f"({100*menor/len(dados):.3f}%) -- verificar se ainda e balde de outliers.")

    # Grava o grupo de cada empresa.
    saida = emp.join(dados["cluster"], how="left")
    saida[["razao_social", "secao_desc", "icci", "cluster"]].to_csv(
        SAIDA / "E6b_cluster_por_empresa.csv")
    return resumo


# ========================================================================
# EXECUÇÃO
# ========================================================================
#
# Lê os dados, separa os ativos e calcula os indicadores em ordem.
def main() -> None:
    print("=== PESQUISA 3 | INFRAESTRUTURA E CAPACIDADE INSTALADA ===\n")
    df, socios = carregar()
    # Separa os estabelecimentos ativos.
    ativos = df[df["ativa"]].copy()
    print(f"Ativos: {len(ativos):,} | Registros de socios: {len(socios):,}\n")

    # Calcula e mostra cada indicador.
    print("E1 - Capital social");         print(e1_capital(ativos), "\n")
    print("E2 - Quadro societario");      print(e2_societario(ativos, socios).head(10), "\n")
    print("E3 - Escopo operacional");     print(e3_escopo(ativos).head(10), "\n")
    print("E4 - Enquadramento tributario"); print(e4_tributario(ativos).head(10), "\n")
    emp = e5_icci(ativos, socios)
    print("E5 - ICCI"); print(emp["estrato_capacidade"].value_counts(), "\n")
    print("E6 - Agrupamento");            print(e6_clusters(emp), "\n")

    print(f"[fim] Resultados em {SAIDA}")


# Ponto de partida quando o script é executado.
if __name__ == "__main__":
    main()

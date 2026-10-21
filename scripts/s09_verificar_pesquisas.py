"""
9. s09_verificar_pesquisas.py
=============================
Confere os resultados das três pesquisas depois que elas rodam.
Só lê e mostra os resultados; não altera nada.

Por que existe: foi esta conferência que encontrou os problemas
corrigidos nas pesquisas (corte de bairros no Gini, mediana do alcance,
grupos do E6 e rótulo do I6).

O que confere:
  1. Composição por posição na cadeia e público-alvo (I1).
  2. Relação entre oferta e demanda (I2).
  3. Concentração por setor (I3).
  4. Contagem de baixados e inaptos usada no I6.
  5. Índice de Gini e ranking de bairros (D1 e D1b).
  6. Por que a mediana do índice de alcance não diferencia os setores (D5).
  7. Tamanho dos grupos de empresas (E6).
  8. Se as faixas do índice de capacidade batem com os percentuais
     definidos (E5).
  9. Extremos das tabelas da Pesquisa 3 que o relatório exibe só em parte.
 10. Estabelecimentos com atividade não informada (código 8888888).

Como rodar (depois das três pesquisas):
    python s09_verificar_pesquisas.py
"""

# Bibliotecas e configurações do projeto.
import pandas as pd
import numpy as np
import s01_config as cfg

# Pastas com os resultados de cada pesquisa.
P1 = cfg.DIR_SAIDAS / "pesquisa_1_comercial"
P2 = cfg.DIR_SAIDAS / "pesquisa_2_distribuicao"
P3 = cfg.DIR_SAIDAS / "pesquisa_3_infraestrutura"

# 1. Mostra a tabela do I1 completa.
print("=" * 72)
print("1) I1 - composicao por elo e orientacao (ativos)")
print("=" * 72)
print(pd.read_csv(P1 / "I1a_composicao_absoluta.csv", index_col=0).to_string())

# 2. Mostra a tabela do I2 com todas as colunas.
print("\n" + "=" * 72)
print("2) I2 - razao oferta/demanda (colunas completas)")
print("=" * 72)
print(pd.read_csv(P1 / "I2_razao_oferta_demanda.csv", index_col=0).to_string())

# 3. Mostra o índice de concentração dos 8 maiores setores.
print("\n" + "=" * 72)
print("3) I3 - HHI por secao (top 8)")
print("=" * 72)
i3 = pd.read_csv(P1 / "I3_hhi_por_secao.csv")
print(i3[["secao_desc", "estabelecimentos", "cnaes_distintos", "hhi",
          "share_dominante_pct", "classificacao"]].head(8).to_string(index=False))

# 4. Confere se o I6 conta só baixados e inaptos (e não todos os não
# ativos), comparando o total do I6 com a contagem direta na base.
print("\n" + "=" * 72)
print("4) I6 - descontinuidade: o rotulo 'baixados_ou_inaptos' confere?")
print("=" * 72)
base = pd.read_parquet(cfg.DIR_BASE / "base_analitica.parquet",
                       columns=["situacao_cadastral"])
vc = base["situacao_cadastral"].value_counts()
nao_ativos = int(vc.sum() - vc.get("02", 0))
baixada_inapta = int(vc.get("08", 0) + vc.get("04", 0))
i6 = pd.read_csv(P1 / "I6_descontinuidade.csv")
print(f"  baixada+inapta na base:          {baixada_inapta:,}")
print(f"  baixada+inapta somada no I6:     {int(i6['baixados_ou_inaptos'].sum()):,}")
print(f"  nula+suspensa (fora da taxa):    {nao_ativos - baixada_inapta:,}"
      f"  ({100*(nao_ativos-baixada_inapta)/len(base):.2f}% da base)")

# 5. Mostra o Gini dos três cortes, os 5 maiores bairros e o peso dos 10 maiores.
print("\n" + "=" * 72)
print("5) D1b - Gini locacional e bairros")
print("=" * 72)
print(pd.read_csv(P2 / "D1b_gini_locacional.csv").to_string(index=False))
d1 = pd.read_csv(P2 / "D1_ranking_bairros.csv", index_col=0)
print(f"  top 5 bairros: {list(d1.index[:5])}")
print(f"  share acumulado dos 10 maiores: {d1['share_municipio_pct'].head(10).sum():.2f}%")

# 6. Mostra por que a mediana do índice de alcance é igual em todos os
# setores: quase todas as empresas têm uma só unidade em um só estado.
print("\n" + "=" * 72)
print("6) D5 - por que indice_alcance_mediano = 1.39 em toda secao?")
print("=" * 72)
# Lê a rede nacional (só unidades ativas) e conta unidades e estados por empresa.
rede = pd.read_parquet(cfg.DIR_BASE / "rede_nacional.parquet")
rede = rede[rede["situacao_cadastral"] == "02"]
perfil = rede.groupby("cnpj_basico").agg(
    unidades=("uf", "size"), ufs=("uf", "nunique"))
print(f"  empresas com matriz ativa no recorte: {len(perfil):,}")
print(f"  mediana de unidades: {perfil['unidades'].median()}")
print(f"  mediana de UFs:      {perfil['ufs'].median()}")
print(f"  ln(1+1)*(1+1) = {np.log1p(1)*2:.4f}  <- valor esperado se u=1,f=1")
print(f"  % com exatamente 1 unidade: {(perfil['unidades']==1).mean()*100:.2f}%")
print(f"  % com exatamente 1 UF:      {(perfil['ufs']==1).mean()*100:.2f}%")
print("\n  distribuicao de unidades por empresa:")
# Distribuição do número de unidades por empresa.
for q in (0.5, 0.75, 0.90, 0.95, 0.99, 1.0):
    print(f"    p{q*100:>5.1f}: {perfil['unidades'].quantile(q):>10,.0f}")
print("\n  => o indice mediano so discrimina no p75+; a mediana e degenerada.")
# Resumo por setor ordenado pelo percentual em mais de um estado.
d5 = pd.read_csv(P2 / "D5b_alcance_por_secao.csv", index_col=0)
print("\n  D5b ordenado por pct_interestadual (metrica que discrimina):")
print(d5.sort_values("pct_interestadual", ascending=False)
      [["empresas", "unidades_medias", "ufs_medias",
        "pct_multiunidade", "pct_interestadual"]].head(8).to_string())

# 7. Mostra o tamanho e o perfil dos grupos de empresas do E6.
print("\n" + "=" * 72)
print("7) E6 - os clusters sao utilizaveis?")
print("=" * 72)
e6 = pd.read_csv(P3 / "E6a_perfil_clusters.csv", index_col=0)
print(e6.to_string())
# Antes da correção do E6, dois grupos tinham 3 e 20 empresas, formados só
# por valores extremos de 'unidades'. Confere se o menor grupo passa de 1%.
menor = int(e6["empresas"].min())
print(f"\n  menor grupo: {menor:,} empresas "
      f"({100*menor/e6['empresas'].sum():.2f}% do total; deve passar de 1%)")
emp_n = pd.read_csv(P3 / "E5a_icci_por_empresa.csv", usecols=["unidades"])
print(f"  unidades: mediana={emp_n['unidades'].median():.0f} "
      f"p99={emp_n['unidades'].quantile(.99):.0f} max={emp_n['unidades'].max():,.0f}")

# 8. Confere se as faixas do índice (25%, 25%, 25%, 15%, 10%) foram respeitadas.
print("\n" + "=" * 72)
print("8) E5 - estratos do ICCI batem com os percentis declarados?")
print("=" * 72)
e5 = pd.read_csv(P3 / "E5a_icci_por_empresa.csv", usecols=["estrato_capacidade"])
vc5 = e5["estrato_capacidade"].value_counts()
# Percentuais esperados de cada faixa e comparação com o obtido.
alvo = {"Muito baixa": 25, "Baixa": 25, "Media": 25, "Alta": 15, "Muito alta": 10}
for k, esperado in alvo.items():
    obtido = 100 * vc5.get(k, 0) / len(e5)
    print(f"  {k:<12} {vc5.get(k,0):>9,}  {obtido:>6.2f}%  (esperado {esperado}%)")
print(f"  total de empresas no ICCI: {len(e5):,}")

# 9. O relatório da Pesquisa 3 exibe só 14 seções no E2 (as maiores) e no
# E5 (as de maior índice). Mostra os extremos na tabela completa, para que
# nenhuma conclusão dependa só das seções exibidas (o mesmo cuidado do I3).
print("\n" + "=" * 72)
print("9) Extremos nas tabelas completas da Pesquisa 3")
print("=" * 72)
e2b = pd.read_csv(P3 / "E2b_societario_por_secao.csv", index_col=0)
e5b = pd.read_csv(P3 / "E5b_icci_por_secao.csv", index_col=0)
for tab, col in ((e2b, "pct_socio_unico"), (e2b, "pct_com_socio_pj"),
                 (e5b, "pct_alta_capacidade")):
    s = tab[col].dropna()
    print(f"  {col:<20} minimo {s.min():6.2f}% ({s.idxmin()})"
          f" | maximo {s.max():6.2f}% ({s.idxmax()})")

# 10. A Receita usa o código 8888888 para atividade não informada. Como a
# classificação do s01_config.py usa os dois primeiros dígitos, esse código
# cai na divisão 88 (assistência social, varejo, B2C). Mostra quantos são.
print("\n" + "=" * 72)
print("10) Atividade nao informada (CNAE 8888888)")
print("=" * 72)
cnae = pd.read_parquet(cfg.DIR_BASE / "base_analitica.parquet",
                       columns=["cnae_fiscal_principal", "situacao_cadastral"])
x = cnae[cnae["cnae_fiscal_principal"] == "8888888"]
print(f"  registros: {len(x):,} | ativos: {int((x['situacao_cadastral'] == '02').sum()):,}")
print(f"  classificacao atribuida: {cfg.classificar_cnae('8888888')}")

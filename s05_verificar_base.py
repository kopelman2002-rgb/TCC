"""
5. s05_verificar_base.py
========================
Reconta a base já montada pelo script s02_extracao_base.py, de forma independente.

Por que existe: o relatório de qualidade do script s02_extracao_base.py arredonda os
percentuais, o que pode esconder casos raros (foi assim que se encontraram
77 registros sem CEP que apareciam como 0,0%). Este script mostra as
contagens exatas. Ele só informa; não altera nada.

O que mostra:
  1. Quantidade de registros de cada tabela.
  2. Registros sem cada informação importante, em número exato.
  3. Distribuição por situação cadastral.
  4. Matrizes e filiais.
  5. Estados com mais unidades na rede nacional.
  6. Valores mais comuns de capital social (confere a conversão para número).
  7. Data de início de atividade mais antiga e mais recente.

Como rodar (depois de cada nova montagem da base):
    python s05_verificar_base.py
"""

# Bibliotecas e configurações do projeto.
import duckdb
import s01_config as cfg

# Abre o banco de dados só para leitura.
con = duckdb.connect(str(cfg.BANCO_DUCKDB), read_only=True)

# 1. Quantidade de registros de cada tabela.
print("=== volumetria das tabelas ===")
for t in ("estabelecimentos", "empresas", "socios", "simples",
          "rede_nacional", "base_analitica", "municipios", "cnaes"):
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t:<18} {n:>12,}")

# 2. Registros sem cada informação, em número exato e em percentual.
print("\n=== ausencias em base_analitica (contagem BRUTA) ===")
q = """
SELECT
  count(*) AS total,
  sum(CASE WHEN bairro IS NULL OR bairro='' THEN 1 ELSE 0 END) AS sem_bairro,
  sum(CASE WHEN cep IS NULL OR cep='00000000' THEN 1 ELSE 0 END) AS sem_cep,
  sum(CASE WHEN capital_social IS NULL THEN 1 ELSE 0 END) AS sem_capital,
  sum(CASE WHEN data_inicio IS NULL THEN 1 ELSE 0 END) AS sem_data_inicio,
  sum(CASE WHEN cnae_fiscal_principal IS NULL THEN 1 ELSE 0 END) AS sem_cnae,
  sum(CASE WHEN cnae_fiscal_principal IS NULL
                OR trim(cnae_fiscal_principal)='' THEN 1 ELSE 0 END) AS sem_cnae_vazio,
  sum(CASE WHEN razao_social IS NULL THEN 1 ELSE 0 END) AS sem_razao,
  sum(CASE WHEN cnae_desc IS NULL THEN 1 ELSE 0 END) AS sem_cnae_desc,
  sum(CASE WHEN natureza_desc IS NULL THEN 1 ELSE 0 END) AS sem_nat_desc,
  sum(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS sem_email
FROM base_analitica
"""
# Executa a contagem e mostra o resultado.
linha = con.execute(q).fetchone()
cols = [d[0] for d in con.execute(q).description]
total = linha[0]
for c, v in zip(cols, linha):
    if c == "total":
        print(f"  {c:<18} {v:>12,}")
    else:
        print(f"  {c:<18} {v:>12,}   ({100.0*v/total:.4f}%)")

# 3. Distribuição por situação cadastral (ativa, baixada, inapta etc.).
print("\n=== quebra por situacao cadastral ===")
rows = con.execute("""
    SELECT situacao_cadastral, count(*) AS n
    FROM base_analitica GROUP BY 1 ORDER BY n DESC
""").fetchall()
mapa = cfg.SITUACAO_CADASTRAL
for sit, n in rows:
    rot = mapa.get(sit, "(fora do dominio)")
    print(f"  {sit!r:<6} {rot:<12} {n:>12,}  ({100.0*n/total:.2f}%)")

# 4. Quantidade de matrizes e de filiais.
print("\n=== matriz x filial ===")
for ident, n in con.execute("""
    SELECT identificador_matriz_filial, count(*) FROM base_analitica
    GROUP BY 1 ORDER BY 2 DESC""").fetchall():
    print(f"  {ident!r:<4} {cfg.MATRIZ_FILIAL.get(ident,'?'):<8} {n:>12,}")

# 5. Os 8 estados com mais unidades na rede nacional.
print("\n=== rede nacional: unidades por UF (top 8) ===")
for uf, n in con.execute("""
    SELECT uf, count(*) FROM rede_nacional GROUP BY 1 ORDER BY 2 DESC LIMIT 8
""").fetchall():
    print(f"  {uf:<4} {n:>10,}")

# 6. Valores mais comuns de capital social.
print("\n=== amostra de capital_social (checar se o cast funcionou) ===")
for r in con.execute("""
    SELECT capital_social, count(*) FROM base_analitica
    GROUP BY 1 ORDER BY 2 DESC LIMIT 5""").fetchall():
    print(f"  {r[0]!r:<20} {r[1]:>10,}")

# 7. Data de início de atividade mais antiga e mais recente.
print("\n=== datas: minimo e maximo de data_inicio ===")
print(" ", con.execute(
    "SELECT min(data_inicio), max(data_inicio) FROM base_analitica").fetchone())

# Fecha o banco.
con.close()

"""
2. s02_extracao_base.py
=======================
Extração e montagem da base de dados. É a primeira etapa do projeto.

O que faz, em ordem:
  1. Define o mês de referência dos dados.
  2. Baixa os 37 arquivos da Receita Federal, retomando de onde parou se a
     conexão cair.
  3. Descompacta os arquivos.
  4. Carrega os dados, filtra o município do Rio de Janeiro e junta as
     informações de empresas, sócios e Simples/MEI.
  5. Grava a base pronta em arquivos Parquet.
  6. Gera um relatório de qualidade dos dados e outro das linhas que a
     leitura descartou por defeito de formato.

Como rodar:
    python s02_extracao_base.py --etapa tudo
    python s02_extracao_base.py --etapa baixar
    python s02_extracao_base.py --etapa descompactar
    python s02_extracao_base.py --etapa construir

Requisitos (a leitura em latin-1 exige o DuckDB 1.2 ou mais recente):
    pip install "duckdb>=1.2" requests tqdm pandas pyarrow
"""

# Bibliotecas usadas pelo script.
from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from datetime import date

import duckdb
import requests
from tqdm import tqdm

# Configurações do projeto (pastas, fonte, recorte, colunas).
import s01_config as cfg


# ========================================================================
# 1. MÊS DE REFERÊNCIA DOS DADOS
# ========================================================================
#
# Define qual mês de dados será usado. Se o mês estiver fixado no
# s01_config.py, usa esse. Se não, procura o mais recente publicado.
def descobrir_competencia(max_meses: int = 8) -> str:
    # Mês fixado no s01_config.py: usa direto.
    if cfg.COMPETENCIA:
        print(f"[info] Competencia fixada em s01_config.py: {cfg.COMPETENCIA}")
        return cfg.COMPETENCIA

    # Começa pelo mês atual e volta um mês por vez.
    hoje = date.today()
    ano, mes = hoje.year, hoje.month
    for _ in range(max_meses):
        comp = f"{ano:04d}-{mes:02d}"
        # Testa se a pasta daquele mês existe no servidor.
        url = f"{cfg.URL_BASE}/{comp}/"
        try:
            r = requests.head(url, timeout=20, allow_redirects=True,
                              auth=cfg.AUTH)
            if r.status_code < 400:
                print(f"[ok] Competencia mais recente encontrada: {comp}")
                return comp
        except requests.RequestException:
            pass
        # Não achou: passa para o mês anterior.
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    # Nenhum mês encontrado: encerra com erro.
    sys.exit("[erro] Nenhuma competencia acessivel. Defina COMPETENCIA em s01_config.py.")


# Monta a lista com o nome dos 37 arquivos a baixar.
def listar_arquivos(competencia: str) -> list[str]:
    nomes: list[str] = []
    for base, n in cfg.ARQUIVOS_PARTICIONADOS.items():
        nomes += [f"{base}{i}.zip" for i in range(n)]
    nomes += [f"{n}.zip" for n in cfg.ARQUIVOS_UNICOS]
    return nomes


# ========================================================================
# 2. DOWNLOAD
# ========================================================================
#
# Baixa os arquivos. Se um download foi interrompido, continua de onde parou.
def baixar(competencia: str) -> None:
    # Lista os arquivos esperados.
    arquivos = listar_arquivos(competencia)
    print(f"[info] {len(arquivos)} arquivos a baixar em {cfg.DIR_ZIPS}")

    for nome in arquivos:
        # Para cada arquivo: define onde salvar e de onde baixar.
        destino = cfg.DIR_ZIPS / nome
        url = f"{cfg.URL_BASE}/{competencia}/{nome}"

        try:
            # Pergunta ao servidor o tamanho do arquivo.
            head = requests.head(url, timeout=30, allow_redirects=True,
                                 auth=cfg.AUTH)
            tamanho_remoto = int(head.headers.get("content-length", 0))
        except requests.RequestException as e:
            # Servidor não respondeu: avisa e pula para o próximo.
            print(f"[aviso] {nome}: indisponivel ({e}). Pulando.")
            continue

        # Verifica quanto do arquivo já foi baixado antes.
        ja_baixado = destino.stat().st_size if destino.exists() else 0
        # Arquivo já completo: não baixa de novo.
        if tamanho_remoto and ja_baixado == tamanho_remoto:
            print(f"[skip] {nome} ja completo.")
            continue
        # Arquivo local maior que o do servidor está corrompido: baixa de novo.
        if tamanho_remoto and ja_baixado > tamanho_remoto:
            print(f"[aviso] {nome}: maior que o do servidor. Baixando de novo.")
            ja_baixado = 0

        # Se já tem uma parte, pede ao servidor só o que falta.
        headers = {"Range": f"bytes={ja_baixado}-"} if ja_baixado else {}

        # Baixa o arquivo em blocos, mostrando o progresso.
        with requests.get(url, stream=True, headers=headers, timeout=120,
                          auth=cfg.AUTH) as r:
            r.raise_for_status()
            # O servidor só continua de onde parou quando responde com o
            # código 206. Se mandar o arquivo inteiro (código 200), grava do
            # início, em vez de acrescentá-lo ao pedaço já baixado.
            if ja_baixado and r.status_code != 206:
                print(f"[aviso] {nome}: o servidor nao continuou o download. "
                      "Baixando do inicio.")
                ja_baixado = 0
            modo = "ab" if ja_baixado else "wb"
            with open(destino, modo) as f, tqdm(
                total=tamanho_remoto, initial=ja_baixado, unit="B",
                unit_scale=True, desc=nome,
            ) as barra:
                for bloco in r.iter_content(chunk_size=1024 * 512):
                    f.write(bloco)
                    barra.update(len(bloco))


# ========================================================================
# 3. DESCOMPACTAÇÃO
# ========================================================================
#
# Extrai os arquivos .zip para a pasta de CSVs.
def descompactar() -> None:
    zips = sorted(cfg.DIR_ZIPS.glob("*.zip"))
    print(f"[info] Descompactando {len(zips)} arquivos em {cfg.DIR_CSVS}")
    for z in zips:
        # Marca cada arquivo já extraído, para não extrair duas vezes.
        marcador = cfg.DIR_CSVS / f".{z.stem}.ok"
        if marcador.exists():
            continue
        try:
            # Extrai o conteúdo do zip.
            with zipfile.ZipFile(z) as zf:
                zf.extractall(cfg.DIR_CSVS)
            marcador.touch()
            print(f"[ok] {z.name}")
        # Zip corrompido: avisa e segue.
        except zipfile.BadZipFile:
            print(f"[erro] {z.name} corrompido. Apague e rebaixe.")


# ========================================================================
# 4. LEITURA E MONTAGEM DA BASE
# ========================================================================
#
# Monta a instrução de leitura dos arquivos da Receita: sem cabeçalho,
# separados por ";", com as colunas na ordem do s01_config.py.
# Tudo é lido como texto; a conversão de números e datas vem depois.
# Linhas com defeito de formato (colunas a mais ou a menos) são descartadas
# e ficam registradas, para o relatório de linhas descartadas (seção 6).
def _sql_leitura(padrao_glob: str, colunas: list[str]) -> str:
    caminho = (cfg.DIR_CSVS / padrao_glob).as_posix()
    nomes = ", ".join(f"'{c}'" for c in colunas)
    return (
        f"read_csv('{caminho}', delim='{cfg.CSV_SEP}', header=false, "
        f"quote='{cfg.CSV_QUOTE}', escape='{cfg.CSV_QUOTE}', "
        f"encoding='{cfg.CSV_ENCODING}', all_varchar=true, "
        f"store_rejects=true, names=[{nomes}])"
    )


# Confere se o código do município do s01_config.py é o mesmo da
# tabela oficial de municípios da Receita.
def _validar_municipio(con: duckdb.DuckDBPyConnection) -> str:
    # Procura o município pelo nome.
    achado = con.execute(
        "SELECT codigo, descricao FROM municipios WHERE upper(descricao) = ?",
        [cfg.MUNICIPIO_ALVO_NOME],
    ).fetchall()
    # Não encontrou: avisa e usa o código do s01_config.py.
    if not achado:
        print(f"[aviso] '{cfg.MUNICIPIO_ALVO_NOME}' nao encontrado na tabela.")
        return cfg.MUNICIPIO_ALVO_CODIGO
    codigo = achado[0][0]
    # Código diferente: avisa e usa o código da tabela oficial.
    if codigo != cfg.MUNICIPIO_ALVO_CODIGO:
        print(f"[aviso] Codigo em s01_config.py ({cfg.MUNICIPIO_ALVO_CODIGO}) "
              f"difere do encontrado ({codigo}). Usando {codigo}.")
    else:
        print(f"[ok] Codigo do municipio validado: {codigo}")
    return codigo


# Monta a base completa do recorte e grava os resultados.
def construir() -> None:
    # Abre o banco de dados e define memória e processamento.
    con = duckdb.connect(str(cfg.BANCO_DUCKDB))
    con.execute("PRAGMA memory_limit='6GB'; PRAGMA threads=4;")

    # 4.1 Tabelas de apoio: CNAE, municípios, naturezas jurídicas etc.
    print("[info] Carregando tabelas de dominio...")
    for tabela in ("cnaes", "municipios", "naturezas", "qualificacoes",
                   "motivos", "paises"):
        con.execute(
            f"CREATE OR REPLACE TABLE {tabela} AS "
            f"SELECT * FROM {_sql_leitura(cfg.GLOB_ARQUIVOS[tabela], cfg.COLS_DOMINIO)}"
        )

    # Confere o código do município.
    cod_mun = _validar_municipio(con)

    # 4.2 Estabelecimentos do recorte. É aqui que o filtro do município
    # do Rio de Janeiro é aplicado. Também organiza os campos: monta o CNPJ
    # completo, converte datas, padroniza bairro e CEP, e troca vazios por nulos.
    print("[info] Filtrando estabelecimentos do municipio alvo...")
    con.execute(f"""
        CREATE OR REPLACE TABLE estabelecimentos AS
        SELECT
            cnpj_basico,
            cnpj_basico || cnpj_ordem || cnpj_dv          AS cnpj_completo,
            cnpj_ordem,
            identificador_matriz_filial,
            nome_fantasia,
            situacao_cadastral,
            TRY_STRPTIME(data_situacao_cadastral,'%Y%m%d')::DATE AS data_situacao,
            motivo_situacao_cadastral,
            TRY_STRPTIME(data_inicio_atividade,'%Y%m%d')::DATE   AS data_inicio,
            cnae_fiscal_principal,
            cnae_fiscal_secundaria,
            trim(upper(bairro))                            AS bairro,
            lpad(regexp_replace(cep,'[^0-9]','','g'), 8, '0') AS cep,
            uf,
            municipio,
            nullif(trim(correio_eletronico),'')            AS email,
            nullif(trim(ddd_1),'')                         AS ddd_1,
            nullif(trim(telefone_1),'')                    AS telefone_1
        FROM {_sql_leitura(cfg.GLOB_ARQUIVOS['estabelecimentos'],
                           cfg.COLS_ESTABELECIMENTOS)}
        WHERE uf = '{cfg.UF_ALVO}' AND municipio = '{cod_mun}'
    """)
    # Mostra quantos estabelecimentos entraram no recorte.
    n_estab = con.execute("SELECT count(*) FROM estabelecimentos").fetchone()[0]
    print(f"[ok] {n_estab:,} estabelecimentos no recorte.")

    # 4.3 Empresas: só as que têm estabelecimento no recorte.
    # O capital social é convertido para número.
    print("[info] Carregando empresas...")
    con.execute(f"""
        CREATE OR REPLACE TABLE empresas AS
        SELECT
            e.cnpj_basico,
            e.razao_social,
            e.natureza_juridica,
            e.qualificacao_responsavel,
            TRY_CAST(replace(e.capital_social, ',', '.') AS DOUBLE) AS capital_social,
            e.porte_empresa
        FROM {_sql_leitura(cfg.GLOB_ARQUIVOS['empresas'], cfg.COLS_EMPRESAS)} e
        SEMI JOIN estabelecimentos x ON x.cnpj_basico = e.cnpj_basico
    """)

    # 4.4 Sócios das empresas do recorte. Nome e CPF ficam de fora.
    print("[info] Carregando quadro societario...")
    con.execute(f"""
        CREATE OR REPLACE TABLE socios AS
        SELECT
            s.cnpj_basico,
            s.identificador_socio,
            s.qualificacao_socio,
            TRY_STRPTIME(s.data_entrada_sociedade,'%Y%m%d')::DATE AS data_entrada,
            s.faixa_etaria,
            s.pais
        FROM {_sql_leitura(cfg.GLOB_ARQUIVOS['socios'], cfg.COLS_SOCIOS)} s
        SEMI JOIN estabelecimentos x ON x.cnpj_basico = s.cnpj_basico
    """)

    # 4.5 Opção pelo Simples Nacional e MEI das empresas do recorte.
    print("[info] Carregando Simples Nacional / MEI...")
    con.execute(f"""
        CREATE OR REPLACE TABLE simples AS
        SELECT
            s.cnpj_basico,
            s.opcao_simples,
            s.opcao_mei,
            TRY_STRPTIME(s.data_opcao_simples,'%Y%m%d')::DATE AS data_opcao_simples,
            TRY_STRPTIME(s.data_opcao_mei,'%Y%m%d')::DATE     AS data_opcao_mei
        FROM {_sql_leitura(cfg.GLOB_ARQUIVOS['simples'], cfg.COLS_SIMPLES)} s
        SEMI JOIN estabelecimentos x ON x.cnpj_basico = s.cnpj_basico
    """)

    # 4.6 Rede nacional: todas as unidades, em qualquer estado, das empresas
    # cuja matriz fica no município. Usada para medir o alcance geográfico
    # na Pesquisa 2.
    print("[info] Mapeando rede nacional das matrizes locais...")
    con.execute(f"""
        CREATE OR REPLACE TABLE rede_nacional AS
        WITH matrizes_locais AS (
            SELECT DISTINCT cnpj_basico FROM estabelecimentos
            WHERE identificador_matriz_filial = '1'
        )
        SELECT
            t.cnpj_basico,
            t.identificador_matriz_filial,
            t.situacao_cadastral,
            t.uf,
            t.municipio,
            t.cnae_fiscal_principal
        FROM {_sql_leitura(cfg.GLOB_ARQUIVOS['estabelecimentos'],
                           cfg.COLS_ESTABELECIMENTOS)} t
        SEMI JOIN matrizes_locais m ON m.cnpj_basico = t.cnpj_basico
    """)

    # 4.7 Base analítica: junta tudo em um registro por estabelecimento,
    # com dados da empresa, descrições, Simples/MEI, idade em meses e
    # quantidade de atividades secundárias. A idade é contada até a data
    # de referência do s01_config.py, e não até o dia em que o script roda.
    print("[info] Montando tabela analitica...")
    con.execute(f"""
        CREATE OR REPLACE TABLE base_analitica AS
        SELECT
            e.*,
            emp.razao_social,
            emp.natureza_juridica,
            emp.capital_social,
            emp.porte_empresa,
            nat.descricao                                   AS natureza_desc,
            cn.descricao                                    AS cnae_desc,
            coalesce(sm.opcao_simples,'N')                  AS opcao_simples,
            coalesce(sm.opcao_mei,'N')                      AS opcao_mei,
            date_diff('month', e.data_inicio,
                      DATE '{cfg.DATA_REFERENCIA}')         AS idade_meses,
            CASE WHEN e.cnae_fiscal_secundaria IS NULL
                      OR trim(e.cnae_fiscal_secundaria) = '' THEN 0
                 ELSE len(str_split(e.cnae_fiscal_secundaria, ',')) END
                                                            AS qtd_cnae_secundario
        FROM estabelecimentos e
        LEFT JOIN empresas    emp ON emp.cnpj_basico = e.cnpj_basico
        LEFT JOIN naturezas   nat ON nat.codigo = emp.natureza_juridica
        LEFT JOIN cnaes       cn  ON cn.codigo  = e.cnae_fiscal_principal
        LEFT JOIN simples     sm  ON sm.cnpj_basico = e.cnpj_basico
    """)

    # 4.8 Grava as tabelas finais em arquivos Parquet.
    print("[info] Exportando Parquet...")
    for tabela in ("base_analitica", "socios", "rede_nacional", "cnaes",
                   "municipios", "naturezas"):
        alvo = (cfg.DIR_BASE / f"{tabela}.parquet").as_posix()
        con.execute(f"COPY {tabela} TO '{alvo}' (FORMAT PARQUET)")

    # Gera os relatórios de qualidade e de linhas descartadas e fecha o banco.
    relatorio_qualidade(con)
    relatorio_linhas_descartadas(con)
    con.close()
    print(f"\n[fim] Base pronta em {cfg.DIR_BASE}")


# ========================================================================
# 5. RELATÓRIO DE QUALIDADE DOS DADOS
# ========================================================================
#
# Calcula o percentual de registros sem bairro, CEP, capital social,
# data de início ou CNAE, e grava em 00_qualidade_dados.csv.
def relatorio_qualidade(con: duckdb.DuckDBPyConnection) -> None:
    print("\n[info] Relatorio de qualidade dos dados")
    df = con.execute("""
        SELECT
            count(*)                                          AS registros,
            count(DISTINCT cnpj_basico)                        AS empresas,
            round(100.0*sum(CASE WHEN bairro IS NULL OR bairro='' THEN 1 ELSE 0 END)
                  /count(*), 2)                                AS pct_sem_bairro,
            round(100.0*sum(CASE WHEN cep IS NULL OR cep='00000000' THEN 1 ELSE 0 END)
                  /count(*), 2)                                AS pct_sem_cep,
            round(100.0*sum(CASE WHEN capital_social IS NULL THEN 1 ELSE 0 END)
                  /count(*), 2)                                AS pct_sem_capital,
            round(100.0*sum(CASE WHEN data_inicio IS NULL THEN 1 ELSE 0 END)
                  /count(*), 2)                                AS pct_sem_data_inicio,
            round(100.0*sum(CASE WHEN cnae_fiscal_principal IS NULL THEN 1 ELSE 0 END)
                  /count(*), 2)                                AS pct_sem_cnae
        FROM base_analitica
    """).df()
    # Mostra o resultado na tela e grava o arquivo.
    print(df.to_string(index=False))
    df.to_csv(cfg.DIR_SAIDAS / "00_qualidade_dados.csv", index=False)


# ========================================================================
# 6. RELATÓRIO DE LINHAS DESCARTADAS NA LEITURA
# ========================================================================
#
# Conta, por arquivo e tipo de defeito, as linhas que a leitura descartou
# (ver _sql_leitura) e grava em 00_linhas_descartadas.csv. Os arquivos de
# estabelecimentos são lidos duas vezes (seções 4.2 e 4.6), por isso a
# contagem considera cada linha uma vez só.
def relatorio_linhas_descartadas(con: duckdb.DuckDBPyConnection) -> None:
    print("\n[info] Linhas descartadas na leitura dos arquivos")
    linhas = []
    try:
        linhas = con.execute("""
            SELECT parse_filename(s.file_path) AS arquivo,
                   e.error_type                AS defeito,
                   count(DISTINCT e.line)      AS linhas
            FROM reject_errors e
            JOIN reject_scans s USING (scan_id, file_id)
            GROUP BY ALL
            ORDER BY arquivo, defeito
        """).fetchall()
    except duckdb.CatalogException:
        # Nenhuma leitura registrou defeito: o registro nem chega a ser criado.
        pass

    # Mostra o resultado na tela e grava o arquivo.
    if linhas:
        for arquivo, defeito, n in linhas:
            print(f"  {arquivo:<40} {defeito:<20} {n:>10,}")
        total = sum(n for _, _, n in linhas)
        print(f"[aviso] {total:,} linha(s) descartada(s) na leitura.")
    else:
        print("[ok] Nenhuma linha descartada.")
    with open(cfg.DIR_SAIDAS / "00_linhas_descartadas.csv", "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arquivo", "defeito", "linhas"])
        w.writerows(linhas)


# ========================================================================
# 7. EXECUÇÃO
# ========================================================================
#
# Lê a etapa pedida e executa as funções correspondentes.
def main() -> None:
    p = argparse.ArgumentParser(description="ETL da base publica de CNPJ")
    p.add_argument("--etapa", default="tudo",
                   choices=["tudo", "baixar", "descompactar", "construir"])
    args = p.parse_args()

    # Executa cada etapa conforme o que foi pedido.
    if args.etapa in ("tudo", "baixar"):
        baixar(descobrir_competencia())
    if args.etapa in ("tudo", "descompactar"):
        descompactar()
    if args.etapa in ("tudo", "construir"):
        construir()


# Ponto de partida quando o script é executado.
if __name__ == "__main__":
    main()

"""
4. s04_verificar_zips.py
========================
Confere se os arquivos baixados estão completos e íntegros.

Por que existe: o script s02_extracao_base.py apenas avisa quando um arquivo falta ou está
corrompido, e continua. Sem esta conferência, a base poderia ser montada
incompleta sem ninguém perceber. Este script para com erro se encontrar
qualquer problema.

O que confere em cada um dos 37 arquivos:
  1. Se o arquivo existe na pasta.
  2. Se o tamanho é igual ao do servidor (detecta download pela metade).
  3. Se o conteúdo do zip está íntegro.

Como rodar:
    python s04_verificar_zips.py
"""

# Bibliotecas usadas pelo script.
from __future__ import annotations

import sys
import zipfile

import requests

import s01_config as cfg


# Monta a lista com o nome dos 37 arquivos esperados.
def arquivos_esperados() -> list[str]:
    nomes: list[str] = []
    for base, n in cfg.ARQUIVOS_PARTICIONADOS.items():
        nomes += [f"{base}{i}.zip" for i in range(n)]
    nomes += [f"{n}.zip" for n in cfg.ARQUIVOS_UNICOS]
    return nomes


# Confere os arquivos e mostra o resultado em forma de tabela.
def main() -> int:
    # Exige que o mês de referência esteja fixado no s01_config.py.
    comp = cfg.COMPETENCIA
    if not comp:
        sys.exit("[erro] COMPETENCIA nao esta fixada em s01_config.py.")

    # Prepara a lista e o cabeçalho da tabela.
    esperados = arquivos_esperados()
    print(f"[info] Verificando {len(esperados)} arquivos da competencia {comp}\n")
    print(f"{'arquivo':<26} {'local (MB)':>12} {'servidor (MB)':>14}  situacao")
    print("-" * 74)

    # Guarda os problemas encontrados e o total em disco.
    problemas: list[str] = []
    total_bytes = 0

    for nome in esperados:
        # Para cada arquivo: define onde está e de onde veio.
        caminho = cfg.DIR_ZIPS / nome
        url = f"{cfg.URL_BASE}/{comp}/{nome}"

        # Conferência 1: o arquivo existe?
        if not caminho.exists():
            print(f"{nome:<26} {'AUSENTE':>12} {'-':>14}  FALTANDO")
            problemas.append(f"{nome}: nao existe em disco")
            continue

        # Tamanho do arquivo no computador.
        local = caminho.stat().st_size
        total_bytes += local

        try:
            # Tamanho do arquivo no servidor.
            r = requests.head(url, timeout=30, allow_redirects=True, auth=cfg.AUTH)
            remoto = int(r.headers.get("content-length", 0))
        except requests.RequestException as exc:
            remoto = 0
            print(f"{nome:<26} {local/1e6:>12,.1f} {'?':>14}  "
                  f"nao consegui consultar o servidor ({type(exc).__name__})")

        # Conferência 2: os tamanhos batem?
        if remoto and local != remoto:
            print(f"{nome:<26} {local/1e6:>12,.1f} {remoto/1e6:>14,.1f}  "
                  f"TAMANHO DIVERGENTE ({local - remoto:+,} bytes)")
            problemas.append(
                f"{nome}: tamanho local {local:,} != servidor {remoto:,}")
            continue

        try:
            # Conferência 3: o conteúdo do zip está íntegro?
            with zipfile.ZipFile(caminho) as zf:
                ruim = zf.testzip()
                membros = len(zf.namelist())
            if ruim is not None:
                print(f"{nome:<26} {local/1e6:>12,.1f} {remoto/1e6:>14,.1f}  "
                      f"CRC INVALIDO em {ruim}")
                problemas.append(f"{nome}: CRC invalido no membro {ruim}")
                continue
        except zipfile.BadZipFile as exc:
            print(f"{nome:<26} {local/1e6:>12,.1f} {remoto/1e6:>14,.1f}  "
                  f"ZIP CORROMPIDO ({exc})")
            problemas.append(f"{nome}: container invalido ({exc})")
            continue

        # Arquivo aprovado nas três conferências.
        print(f"{nome:<26} {local/1e6:>12,.1f} {remoto/1e6:>14,.1f}  "
              f"ok ({membros} membro{'s' if membros != 1 else ''})")

    print("-" * 74)
    # Mostra o total baixado.
    print(f"Total em disco: {total_bytes/1e9:.2f} GB")

    # Se houve problema: lista, orienta o que fazer e encerra com erro.
    if problemas:
        print(f"\n[erro] {len(problemas)} problema(s) encontrado(s):")
        for p in problemas:
            print(f"  - {p}")
        print("\nApague os arquivos citados e rode: "
              "python s02_extracao_base.py --etapa baixar")
        return 1

    # Tudo certo.
    print(f"\n[ok] Os {len(esperados)} arquivos estao completos e integros.")
    return 0


# Ponto de partida quando o script é executado.
if __name__ == "__main__":
    sys.exit(main())

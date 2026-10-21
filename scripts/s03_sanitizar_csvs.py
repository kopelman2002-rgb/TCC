"""
3. s03_sanitizar_csvs.py
========================
Corrige caracteres inválidos nos arquivos da Receita Federal.

Por que existe: alguns bytes dos arquivos não pertencem à codificação
declarada (latin-1), e isso impedia a carga da base. Na competência
2026-08 foram 5 bytes em cerca de 27 GB.

O que faz:
  1. Procura esses bytes em todos os arquivos descompactados.
  2. Troca cada um por um espaço, sem alterar o tamanho do arquivo.
     Depois, o script s02_extracao_base.py transforma esse espaço em campo vazio.
  3. Registra cada troca em saidas/00_bytes_sanitizados.csv.

A troca é reversível: basta extrair os arquivos .zip de novo.
Rodar outra vez não altera nada, porque não há mais o que corrigir.

Como rodar:
    python s03_sanitizar_csvs.py            # corrige
    python s03_sanitizar_csvs.py --simular  # só mostra, não altera
"""

# Bibliotecas usadas pelo script.
from __future__ import annotations

import argparse
import csv
import glob
import os

import s01_config as cfg

# Faixa de bytes considerados inválidos.
FAIXA = range(0x80, 0xA0)
# Caractere que entra no lugar (espaço).
SUBSTITUTO = 0x20          # espaco
# Tamanho de cada pedaço lido do arquivo (16 MB).
BLOCO = 16 * 1024 * 1024


# Procura os bytes inválidos em um arquivo e devolve, para cada um,
# a posição, o byte e o texto ao redor.
def varrer(caminho: str) -> list[tuple[int, int, str]]:
    achados: list[tuple[int, int, str]] = []
    offset = 0
    with open(caminho, "rb") as f:
        while True:
            # Lê o arquivo em pedaços.
            bloco = f.read(BLOCO)
            if not bloco:
                break
            # Procura cada byte inválido dentro do pedaço.
            for b in FAIXA:
                i = -1
                while True:
                    i = bloco.find(b, i + 1)
                    if i < 0:
                        break
                    # Guarda o texto ao redor, para conferência.
                    ctx = bloco[max(0, i - 70):i + 70]
                    ctx = (ctx.decode("latin-1", "replace")
                           .replace("\n", "\\n").replace("\r", "\\r"))
                    achados.append((offset + i, b, ctx))
            # Avança a posição para o próximo pedaço.
            offset += len(bloco)
    return achados


# Executa a varredura e a correção.
def main() -> int:
    # Lê a opção --simular.
    p = argparse.ArgumentParser(description="Higieniza bytes C1 nos CSVs da RFB")
    p.add_argument("--simular", action="store_true",
                   help="apenas relata; nao altera arquivo algum")
    args = p.parse_args()

    # Lista os arquivos descompactados (ignora os marcadores ocultos).
    arquivos = sorted(
        c for c in glob.glob(str(cfg.DIR_CSVS / "*"))
        if os.path.isfile(c) and not os.path.basename(c).startswith(".")
    )
    print(f"[info] Varrendo {len(arquivos)} arquivos em {cfg.DIR_CSVS}")
    if args.simular:
        print("[info] Modo simulacao: nada sera escrito.\n")

    # Varre arquivo por arquivo.
    registros = []
    for caminho in arquivos:
        achados = varrer(caminho)
        if not achados:
            continue
        nome = os.path.basename(caminho)
        # Mostra na tela cada byte encontrado e guarda para o registro.
        print(f"\n[!] {nome}: {len(achados)} byte(s) fora do ISO-8859-1")
        for offset, b, ctx in achados:
            print(f"    offset {offset:>15,}  0x{b:02X}")
            print(f"      {ctx.encode('ascii', 'backslashreplace').decode()}")
            registros.append({
                "arquivo": nome,
                "offset": offset,
                "byte_original": f"0x{b:02X}",
                "byte_substituto": f"0x{SUBSTITUTO:02X}",
                "contexto": ctx,
            })

        if not args.simular:
            # Troca cada byte inválido por espaço, direto no arquivo.
            with open(caminho, "r+b") as f:
                for offset, _b, _ctx in achados:
                    f.seek(offset)
                    f.write(bytes([SUBSTITUTO]))
            print(f"    -> {len(achados)} byte(s) substituido(s) por espaco.")

    # Nada encontrado: encerra.
    if not registros:
        print("\n[ok] Nenhum byte invalido encontrado. Nada a fazer.")
        return 0

    if args.simular:
        # Modo simulação: só informa quantos seriam trocados.
        print(f"\n[info] {len(registros)} byte(s) seriam alterados.")
        return 0

    # Grava o registro de todas as trocas feitas.
    destino = cfg.DIR_SAIDAS / "00_bytes_sanitizados.csv"
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "arquivo", "offset", "byte_original", "byte_substituto", "contexto"])
        w.writeheader()
        w.writerows(registros)

    print(f"\n[ok] {len(registros)} byte(s) sanitizado(s).")
    print(f"[ok] Trilha de auditoria: {destino}")
    return 0


# Ponto de partida quando o script é executado.
if __name__ == "__main__":
    raise SystemExit(main())

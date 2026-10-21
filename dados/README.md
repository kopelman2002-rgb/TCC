# dados

Pasta de trabalho dos scripts. Os arquivos não são versionados (ver `.gitignore`): somam cerca de 7,7 GB compactados e 27 GB descompactados, e parte das saídas contém a razão social de MEI, que inclui o nome do empresário.

Os scripts criam e preenchem as subpastas:

| Pasta | Conteúdo | Criada por |
|---|---|---|
| `01_zips/` | 37 arquivos `.zip` da competência 2026-08 | `s02_extracao_base.py --etapa baixar` |
| `02_csvs/` | Arquivos descompactados | `s02_extracao_base.py --etapa descompactar` |
| `03_base/` | Banco DuckDB e tabelas Parquet do recorte do município | `s02_extracao_base.py --etapa construir` |

Fonte: Dados Abertos do CNPJ, Receita Federal do Brasil (endereço e código de acesso em `scripts/s01_config.py`).

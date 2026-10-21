# Dados abertos do CNPJ e inteligência artificial: análise do tecido empresarial do município do Rio de Janeiro

Código e relatórios do Projeto de Graduação de Eduardo Kopelman, apresentado ao Departamento de Engenharia Industrial da PUC-Rio como requisito parcial para a obtenção do título de Engenheiro de Produção (2026). Orientador: Prof. Gustavo Costa Gomes Moreira.

O trabalho converte a base pública do CNPJ da Receita Federal (competência 2026-08) em três pesquisas sobre as empresas do município do Rio de Janeiro: dimensão comercial, distribuição física e alcance, e infraestrutura e capacidade instalada. A análise foi conduzida em duas execuções com um assistente de inteligência artificial, uma com os scripts deste repositório e outra sem roteiro, e o trabalho compara os produtos das duas.

## Estrutura

```
scripts/                         pipeline da execução com scripts (Quadro 5 do TCC)
  s01_config.py                  configurações: pastas, fonte, leiaute, recorte e taxonomia CNAE
  s02_extracao_base.py           download, descompactação e montagem da base (DuckDB/Parquet)
  s03_sanitizar_csvs.py          correção dos bytes fora da codificação, com trilha de auditoria
  s04_verificar_zips.py          conferência dos 37 arquivos baixados
  s05_verificar_base.py          recontagem independente da base
  s06_pesquisa_comercial.py      Pesquisa 1: dimensão comercial
  s07_pesquisa_distribuicao.py   Pesquisa 2: distribuição física e alcance
  s08_pesquisa_infraestrutura.py Pesquisa 3: infraestrutura e capacidade instalada
  s09_verificar_pesquisas.py     conferência das saídas das pesquisas
  s10_gerar_bi.py                geração dos relatórios em HTML
relatorios/
  execucao_com_scripts/          relatórios gerados pelo s10
  execucao_sem_roteiro/          painéis da execução sem roteiro, como entregues pelo assistente
dados/                           pasta de trabalho (conteúdo não versionado)
```

Os relatórios abrem direto no navegador. Os textos de leitura deles foram mantidos como estavam na execução avaliada no TCC, inclusive as divergências apontadas no Quadro 8 do trabalho.

## Como reproduzir

Requisitos: Python 3.10 ou mais recente e as bibliotecas de `requirements.txt`:

```
pip install -r requirements.txt
```

Na pasta `scripts/`, rode em ordem:

```
python s02_extracao_base.py --etapa baixar
python s04_verificar_zips.py
python s02_extracao_base.py --etapa descompactar
python s03_sanitizar_csvs.py
python s02_extracao_base.py --etapa construir
python s05_verificar_base.py
python s06_pesquisa_comercial.py
python s07_pesquisa_distribuicao.py
python s08_pesquisa_infraestrutura.py
python s09_verificar_pesquisas.py
python s10_gerar_bi.py
```

Os arquivos baixados e a base ficam em `dados/`; as tabelas, os gráficos e os relatórios, em `saidas/`. Nenhum dos dois vai para o repositório, porque somam dezenas de gigabytes e parte das saídas contém a razão social de MEI, que inclui o nome do empresário.

A fonte é um compartilhamento público da Receita Federal acessado por WebDAV, cujo endereço já mudou durante o trabalho. Se o download falhar, confira o endereço e o código de acesso em `scripts/s01_config.py`.

## Histórico do código

A versão executada no trabalho, em 17/09/2026, é a do commit [`6f0ec66`](https://github.com/kopelman2002-rgb/TCC/tree/6f0ec66339d7242d3a6326d80ee224ec6ef47049). A revisão de outubro de 2026 reorganizou as pastas e fez estas correções:

- A idade das empresas passou a ser contada até a data fixa `DATA_REFERENCIA` (17/09/2026), e não até o dia em que o script roda. Como a contagem é em meses de calendário, a base montada de novo reproduz as idades usadas no trabalho; o `s05` confere isso.
- A leitura dos arquivos da Receita registra as linhas descartadas por defeito de formato em `saidas/00_linhas_descartadas.csv`.
- O download recomeça do zero quando o servidor não aceita continuar um arquivo pela metade, ou quando o arquivo local é maior que o do servidor. Antes, o arquivo podia ser gravado em dobro.
- A curva de Lorenz do Gini locacional passou a começar na origem (0, 0). No corte de 300 estabelecimentos, a diferença é da ordem de 0,000002 e não deve alterar o valor publicado com quatro casas (0,5710).
- O ICCI registra em `E5c_valores_ausentes_icci.csv` quantos valores ausentes receberam escore 0, com o mesmo resultado de antes.
- A exigência de versão do DuckDB foi corrigida para 1.2 ou mais recente (a leitura em latin-1 não existe nas versões anteriores).
- O `s09` ganhou conferências dos extremos das tabelas que o relatório exibe só em parte e da atividade não informada (CNAE 8888888). O `s10` avisa quando a base muda, porque os textos de leitura foram escritos para a competência 2026-08.

Foram mantidas, por serem discutidas no TCC, a contagem de sócio único do E2, que inclui empresas sem sócio registrado, e a atribuição de um sócio a essas empresas no ICCI.

## Como citar

Ver `CITATION.cff`:

> KOPELMAN, Eduardo. **Dados abertos do CNPJ e inteligência artificial: análise do tecido empresarial do município do Rio de Janeiro**. 2026. Projeto de Graduação (Engenharia de Produção) – Pontifícia Universidade Católica do Rio de Janeiro, Rio de Janeiro, 2026.

## Licença

O código está sob a licença MIT (`LICENSE`). Os dados de origem são públicos e pertencem à Receita Federal do Brasil.

# auditoria - app_vulneravel.py

| # | falha | owasp 2025 | impacto | correcao aplicada |
|---|---|---|---|---|
| 1 | sql injection em `/api/usuarios/buscar` (nome concatenado direto na query) | A05 - injecao | qualquer um le a tabela inteira, inclusive coluna senha, so mandando `' OR '1'='1` | trocado pra query parametrizada `%s`, banco escapa o valor |
| 2 | xss refletido em `/perfil` (input do usuario devolvido cru no html) | A05 - injecao | script arbitrario roda no navegador de quem clicar num link malicioso com `?u=` | escape manual com `markupsafe.escape` antes de montar o html |
| 3 | `DELETE /api/usuarios/<id>` sem nenhuma autenticacao | A01 - controle de acesso quebrado | qualquer requisicao apaga qualquer usuario, sem credencial nenhuma | exige header `X-API-Key`, 401 sem header e 403 se a key nao for a admin |
| 4 | `/api/relatorio` deixa a excecao subir e o flask (com debug=true) devolve o traceback completo pro cliente | A10 - tratamento inadequado de condicoes excepcionais | vaza nome de tabela, stack de codigo e versao de biblioteca pra quem so mandou um get | error handler generico: loga o traceback no servidor, devolve so `{"erro":"erro interno"}` |
| 5 | resposta de `/api/usuarios/buscar` usa `SELECT *`, entao a coluna `senha` volta no json | A04 - falhas criptograficas (exposicao de dado sensivel) | hash de senha (ou pior, senha em texto puro) trafega em toda busca de usuario | select explicito so com `id, nome, email` |
| 6 | senha do banco (`password="senha"`) e `SENHA_MESTRA` escritas direto no codigo | A02 - configuracao incorreta | quem le o repositorio (ou um vazamento de codigo-fonte) ja tem a credencial do banco | credenciais lidas de variavel de ambiente, o processo nao sobe sem elas |
| 7 (ausencia) | nenhum header de seguranca em lugar nenhum do arquivo (sem CSP, sem X-Frame-Options, sem X-Content-Type-Options) | A02 - configuracao incorreta | navegador roda com as protecoes padrao desligadas, facilita clickjacking e mime sniffing | `after_request` fixo aplicando os 3 headers em toda resposta |
| 8 (ausencia) | nenhum log de quem fez o que (nem no delete, nem em erro) | A09 - falhas de log e alerta | usuario apagado ou erro de banco nao deixa rastro nenhum pra investigar depois | `logging` registrando delete e excecao no servidor |

## bonus - `app.run(debug=True)`

alem das 8 acima, rodar com `debug=True` em qualquer ambiente exposto liga o werkzeug debugger interativo, que permite executar codigo python arbitrario no servidor por quem achar o endpoint de erro (A02 - configuracao incorreta). corrigido com `debug=False` fixo em `app_seguro.py`.

## nota sobre a lista owasp usada

a owasp mudou a numeracao no top 10 2025 em relacao a 2021: injecao passou
de A03 pra A05, configuracao incorreta de A05 pra A02, falhas criptograficas
de A02 pra A04, e entrou uma categoria nova (A10 - tratamento inadequado de
condicoes excepcionais) que nao existia em 2021 e cobre exatamente o caso
do item 4 (excecao que sobe crua ate o cliente). controle de acesso (A01)
e falhas de log (A09, so mudou o nome) ficaram na mesma posicao.

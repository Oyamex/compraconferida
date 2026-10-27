# Site da Compra Conferida

Site estático no GitHub Pages (`compraconferida.com.br`), gerado por `gerar.py` a partir dos dados de cada vídeo. As páginas `.html` da raiz e as pastas `<n>/` são **saída do gerador**: não editar à mão.

## Como gerar

```powershell
$py = "D:\CLAUDE\ferramentas-video\voz-supertonic\Scripts\python.exe"
& $py -I gerar.py            # publica: escreve aqui, só com dados/*.json reais
& $py -I gerar.py --previa   # prévia com os exemplos, em ..\previa-site (fora do Git)
```

Prévia local: servidor `site-compraconferida` (porta 8767) no `.claude/launch.json` do Projeto Vídeo, que serve `previa-site`.

## Onde fica cada coisa

| Arquivo | O que é |
|---|---|
| `dados/<n>.json` | um vídeo = uma página `/<n>/`. Mesmo conteúdo que monta o Short no motor |
| `dados/exemplos/` | exemplos fictícios (`"exemplo": true`); o gerador se recusa a publicá-los |
| `fonte/*.html` | miolo das páginas de texto (título e descrição nos comentários do topo) |
| `estilo.css` | sistema visual; para adaptar, mudar só os tokens de `:root` |
| `gerar.py` | monta início, páginas de vídeo, texto, 404, `sitemap.xml` e `robots.txt` |

## Formato dos dados

`formato: "c2"` (dois produtos: `a`, `b`, `rodadas`, `seA`, `seB`) ou `"c1"` (um produto: `produto`, `bom`, `ruim`, `compreSe`, `naoCompreSe`). Comuns: `numero`, `data` e `conferidoEm` (AAAA-MM-DD), `categoria`, `gancho`, `youtube` (id do vídeo, opcional), `titulo` e `descricao` (opcionais; sem eles o gerador escreve "X ou Y: qual comprar?").

Cada produto: `nome`, `apelido`, `preco`, `precoDe`, `historico` (preços diários, o último é hoje), `nota`, `vendas`, `foto` (URL), `disponivel` (false mostra "indisponível") e `lojas: [{loja, preco, url}]`, com `loja` em `shopee`, `mercadolivre`, `amazon` ou `tiktok`. O botão da loja mais barata vem primeiro e em destaque.

## Regras de conteúdo

- Todo valor em dinheiro leva "R$".
- **Desconto real ou de vitrine:** o preço do dia contra a mediana do `historico`. 5% ou mais abaixo é "desconto real"; "de R$" alto com preço na mediana é "desconto de vitrine". Precisa de 7 dias de histórico ou mais.
- Links de loja com `rel="sponsored nofollow noopener"` (exigência do Google para links pagos).
- Nota e vendas da loja aparecem na tela como "na loja", mas **não** vão para os dados estruturados: o Google não aceita nota de terceiros como `aggregateRating`.
- Só citar no site os programas de afiliado em que a conta já está aprovada (a frase da Amazon entra quando a conta existir).

## SEO feito

- Título e descrição únicos por página, `canonical`, Open Graph, `lang="pt-BR"`.
- Dados estruturados: `Organization` e `WebSite` no início; em cada vídeo, `WebPage`, `BreadcrumbList`, `ItemList` de `Product` com `Offer` por loja e `FAQPage`; no formato de um produto, `Review` com prós e contras (`positiveNotes`/`negativeNotes`).
- `sitemap.xml` com `lastmod` = data da conferência; `robots.txt` aponta o mapa.
- Endereço curto: `/12` abre `/12/` (o GitHub Pages redireciona sozinho para a pasta).
- Sem fonte externa nem biblioteca: só CSS e um script pequeno na busca. Imagens com `loading="lazy"` e tamanho declarado.
- `.nojekyll`: o Pages serve os arquivos como estão.

## Aprendizados

- **Enforce HTTPS:** depois de apontar o DNS, o GitHub leva um tempo para emitir o certificado, e a opção fica cinza mais um pouco mesmo com o HTTPS funcionando. Ligada em 27/10/2026; `http://` responde 301 para `https://`.
- **Repositório público:** o GitHub Pages grátis só publica de repositório público. Por isso não entra aqui nada que não possa ser visto por todos: nem chave, nem estratégia, nem dado pessoal.
- **Grade no celular:** colunas `1fr` não encolhem abaixo do conteúdo; usar `minmax(0, 1fr)` para não estourar a largura.
- **Tabela larga:** sempre dentro de `.rolagem`; no celular a coluna "Quem leva" some, porque a cor já mostra quem venceu.
- **Ordem do CSS:** regra de `@media` escrita antes da regra base perde para ela. Ajustes de celular vão depois do componente.
- **Python no Windows:** o terminal usa cp1252; `print` com seta ou acento quebra. Mensagens do gerador ficam sem esses caracteres.
- **Porta da prévia:** outro chat pode estar com a 8765 ocupada; a prévia do site usa a 8767.
- **Open API da Shopee Afiliados:** GraphQL em `open-api.affiliate.shopee.com.br/graphql`. Cabeçalho `Authorization: SHA256 Credential=<AppID>, Timestamp=<unix>, Signature=<sha256(AppID+Timestamp+corpo+Senha)>`, com o corpo assinado idêntico ao enviado (JSON compacto). Sem cabeçalho: "Invalid Authorization Header"; assinatura certa sem acesso liberado: erro 10035. Consultas usadas: `productOfferV2` (busca de ofertas) e `generateShortLink` (link curto com até 5 `subIds`, como `v12 site c2 A`). O cliente fica fora deste repositório.
- **Limites da Open API da Shopee** (documento oficial, visão geral): 8.000 chamadas por hora; consultas de várias páginas usam `scrollId` (até 500 itens por página, vale uma vez só e por 30 s, e a consulta sem `scrollId` precisa de 30 s de intervalo); o relatório de conversões cobre só os últimos 3 meses. O explorador (`open-api.affiliate.shopee.com.br/explorer/v2`) e a leitura do esquema também pedem a credencial (erro 10020 sem cabeçalho). Há um "Product Feed Offer List", o catálogo inteiro de ofertas, melhor para o robô de preços que buscar produto por produto.
- **Assinatura da Shopee conferida com o documento "Authentication":** `SHA256(AppID + Timestamp + corpo + Senha)` em hexadecimal minúsculo, e o relógio pode diferir no máximo 10 minutos do servidor. O documento escreve "Credentials=" na estrutura, mas "Credential=" no exemplo; o servidor aceita "Credential=". O hash do exemplo do documento (`dc88d7…`) não se reproduz com o texto mostrado na página, nem variando espaços e quebras de linha. A fórmula é a mesma; a prova final só vem com a credencial verdadeira.
- **`shopeeOfferV2`** lista campanhas (coleções e categorias com comissão e período), não produtos. Serve para achar as categorias de comissão alta do nicho.
- **Acesso à Open API da Shopee:** a Central de Ajuda do Brasil não explica como pedir o AppID (conferido em 27/10/2026); o único caminho citado no painel é "entre em contato", pelo formulário de Afiliados (resposta em até 3 dias úteis). **Alternativa sem API:** no painel web, "Oferta de Produto" → marcar os produtos → "Obter Link" (com até 5 Sub IDs) baixa um CSV com a coluna "Offer Link". No app, "Link de Conversão" converte até 5 links por vez.
- **Como pedir a Open API da Shopee (achado em 27/10/2026):** Central de Ajuda → "E-mail" (formulário de Afiliados) → "já sou afiliado: Sim" → login "Não" → tema "Tenho dúvidas/dificuldades com meu cadastro / conta" → cenário **"Quero ativar a API"**. O tema "ferramentas de promoção" não tem a opção. Prazo informado: até 3 dias úteis.
- **Sub_id da Shopee só aceita letras e números** (a-z, A-Z, 0-9): nada de hífen, espaço ou acento. Padrão do projeto, um campo por informação, para o relatório separar sozinho: Sub_id1 o vídeo (`v12`), Sub_id2 o lugar (`site`, `tiktok`, `instagram`, `youtube`, `pinterest`), Sub_id3 o formato (`c1` ou `c2`), Sub_id4 o produto (`A` ou `B`). No painel, "Link personalizado" converte até 5 links por vez com os mesmos Sub_ids.
- **Histórico de preço da Shopee (conferido em 27/10/2026):** não há fonte grátis e confiável do passado. Buscapé e Zoom mostram histórico só na tela, sem API, e cobrem mal a Shopee; o Keepa é só Amazon e pago; extensões de navegador não têm prova para o Brasil; raspar a página fere os termos. A Open API dá só o preço do dia. Por isso o `historico` dos dados é nosso: uma leitura por dia do mesmo anúncio linkado, pela API ou pelo "Feed de produto" do painel de Afiliados.
- **Número do vídeo:** o campo `numero` dos dados é a única fonte. O motor do Short mostra o selo "Nº n" no pé da tela o vídeo inteiro e `compraconferida.com.br/n` no fecho; o gerador cria `/n/`; o Sub_id1 é `vn`. Antes de publicar, os números da tela, da fala, dos dados, da página e do Sub_id têm de ser iguais.

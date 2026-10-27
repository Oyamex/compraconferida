"""Gera o site da Compra Conferida a partir dos dados dos vídeos.

    python -I gerar.py            publica: escreve na própria pasta do site (só dados reais)
    python -I gerar.py --previa   prévia local com os exemplos, em ../previa-site (fora do Git)

Entrada: dados/<n>.json (um por vídeo, o mesmo conteúdo que monta o Short no motor) e fonte/*.html
(páginas de texto). Saída: index.html, <n>/index.html, transparencia.html, privacidade.html,
404.html, sitemap.xml e robots.txt. Nada é escrito à mão nas páginas geradas.
"""
import html
import json
import shutil
import statistics
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SITE = "https://compraconferida.com.br"
MARCA = "Compra Conferida"
ESTATICOS = ["estilo.css", "marca.svg", "og.png", "CNAME", ".nojekyll"]
LOJAS = {
    "shopee": ("Shopee", "S"),
    "mercadolivre": ("Mercado Livre", "ML"),
    "amazon": ("Amazon", "A"),
    "tiktok": ("TikTok Shop", "T"),
}

e = html.escape


# ---------- formatos ----------

def reais(v):
    """R$ 289 ou R$ 1.299,90 (todo valor leva R$, regra do usuário)."""
    inteiro = round(v, 2) == int(v)
    txt = f"{v:,.0f}" if inteiro else f"{v:,.2f}"
    return "R$ " + txt.replace(",", "X").replace(".", ",").replace("X", ".")


def dia(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def milhar(n):
    return f"{n:,}".replace(",", ".")


def lojas_ordenadas(p):
    return sorted(p.get("lojas", []), key=lambda l: l["preco"])


def melhor_preco(p):
    ls = lojas_ordenadas(p)
    return ls[0]["preco"] if ls else p["preco"]


def desconto(p):
    """Compara o preço do dia com o preço mais comum do histórico (mediana)."""
    hist = p.get("historico") or []
    preco = melhor_preco(p)
    if len(hist) < 7:
        return None
    normal = statistics.median(hist[:-1])
    queda = 1 - preco / normal
    dias = len(hist)
    if queda >= 0.05:
        menor = preco <= min(hist)
        txt = f"Desconto real: {round(queda * 100)}% abaixo do normal"
        return {"tom": "bom", "texto": txt, "curto": f"−{round(queda * 100)}% real",
                "extra": f"Menor preço em {dias} dias" if menor else "", "normal": normal}
    if p.get("precoDe", 0) > preco:
        return {"tom": "ruim", "texto": f"Desconto de vitrine: {reais(preco)} é o preço de sempre",
                "curto": "Desconto de vitrine", "extra": "", "normal": normal}
    return {"tom": "neutro", "texto": "Preço normal", "curto": "Preço normal", "extra": "", "normal": normal}


def produtos(d):
    return [d["a"], d["b"]] if d["formato"] == "c2" else [d["produto"]]


def titulo(d):
    if d.get("titulo"):
        return d["titulo"]
    if d["formato"] == "c2":
        return f'{d["a"]["nome"]} ou {d["b"]["nome"]}: qual comprar?'
    return f'{d["produto"]["nome"]} vale a pena? O desconto é real?'


def descricao(d):
    if d.get("descricao"):
        return d["descricao"]
    if d["formato"] == "c2":
        a, b = d["a"], d["b"]
        return (f'{a["nome"]} por {reais(melhor_preco(a))} ou {b["nome"]} por {reais(melhor_preco(b))}? '
                f'Comparamos preço real, defeitos citados e para quem cada um vale a pena. Preço conferido em {dia(d["conferidoEm"])}.')
    p = d["produto"]
    return (f'{p["nome"]} por {reais(melhor_preco(p))}: o desconto é real? O que os compradores elogiam e reclamam, '
            f'e para quem vale a pena. Preço conferido em {dia(d["conferidoEm"])}.')


# ---------- peças de página ----------

def cabeca(tit, desc, caminho, extra=""):
    url = SITE + caminho
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(tit)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#146c47">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{MARCA}">
<meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{e(tit)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og.png">
<meta name="twitter:card" content="summary">
<link rel="icon" href="/marca.svg" type="image/svg+xml">
<link rel="stylesheet" href="/estilo.css">
{extra}</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo"><div class="caixa">
  <a class="logo" href="/"><img src="/marca.svg" alt="" width="30" height="30">{MARCA}</a>
  <nav class="menu" aria-label="Principal"><a href="/#comparacoes">Comparações</a><a class="opcional" href="/#como">Como conferimos</a><a class="opcional" href="/transparencia.html">Transparência</a></nav>
</div></header>
"""


def rodape(script=""):
    return f"""<footer class="rodape"><div class="caixa">
  <div>
    <a class="logo" href="/"><img src="/marca.svg" alt="" width="26" height="26">{MARCA}</a>
    <p>Antes de comprar, a gente confere. Links de lojas parceiras podem render comissão, sem mudar o seu preço.</p>
  </div>
  <p><a href="/transparencia.html">Transparência</a> · <a href="/privacidade.html">Privacidade</a> · <a href="mailto:compraconferida@gmail.com">Contato</a><br>© {date.today().year} {MARCA}</p>
</div></footer>
{script}</body>
</html>
"""


def json_ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"


def foto(p, classe="foto"):
    if p.get("foto"):
        return f'<div class="{classe}"><img src="{e(p["foto"])}" alt="{e(p["nome"])}" loading="lazy" width="400" height="300"></div>'
    return (f'<div class="{classe} sem-foto" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.5"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="11" r="2"/>'
            '<path d="m21 17-5-5-8 7"/></svg></div>')


def botao_loja(l, n, principal):
    nome, sigla = LOJAS.get(l["loja"], (l["loja"].title(), l["loja"][:1].upper()))
    classe = "botao-loja" + (" principal" if principal else "")
    return (f'<a class="{classe}" href="{e(l["url"])}" rel="sponsored nofollow noopener" target="_blank" '
            f'data-loja="{e(l["loja"])}" data-video="{n}"><span class="sigla s-{e(l["loja"])}">{sigla}</span>'
            f'<span class="onde">Ver na {nome}</span><span class="valor numero">{reais(l["preco"])}</span>'
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg></a>')


def grafico(p):
    hist = p.get("historico") or []
    if len(hist) < 2:
        return ""
    lo, hi = min(hist), max(hist)
    faixa = (hi - lo) or 1
    w, h, m = 300, 80, 8
    pts = [(round(i * w / (len(hist) - 1), 1), round(m + (hi - v) * (h - 2 * m) / faixa, 1)) for i, v in enumerate(hist)]
    linha = " ".join(f"{x},{y}" for x, y in pts)
    area = f"0,{h} " + linha + f" {w},{h}"
    x, y = pts[-1]
    return (f'<figure class="historico"><svg viewBox="0 0 {w} {h}" role="img" preserveAspectRatio="none" '
            f'aria-label="Preço de {e(p["nome"])} nos últimos {len(hist)} dias, de {reais(lo)} a {reais(hi)}">'
            f'<polygon points="{area}" class="area"/><polyline points="{linha}" class="linha"/>'
            f'<circle cx="{x}" cy="{y}" r="4"/></svg>'
            f'<figcaption><span>{len(hist)} dias atrás</span><span>mín. {reais(lo)} · máx. {reais(hi)}</span><span>hoje</span></figcaption></figure>')


def cartao_produto(p, d, rotulo=None, vencedor=False):
    n = d["numero"]
    ds = desconto(p)
    ls = lojas_ordenadas(p)
    selo = f'<span class="selo {ds["tom"]}">{e(ds["curto"])}</span>' if ds else ""
    antes = f'<span class="antes numero">{reais(p["precoDe"])}</span>' if p.get("precoDe", 0) > melhor_preco(p) else ""
    estrelas = ""
    if p.get("nota"):
        estrelas = (f'<p class="nota"><span class="estrelas" style="--n:{p["nota"]}" aria-hidden="true"></span>'
                    f'<b>{str(p["nota"]).replace(".", ",")}</b> na loja')
        if p.get("vendas"):
            estrelas += f' · {milhar(p["vendas"])} vendidos'
        estrelas += "</p>"
    indisponivel = '<p class="indisponivel">Indisponível no momento</p>' if p.get("disponivel") is False else ""
    botoes = "".join(botao_loja(l, n, i == 0) for i, l in enumerate(ls))
    marca_rotulo = f'<span class="rotulo">{e(rotulo)}</span>' if rotulo else ""
    coroa = '<span class="selo destaque">Mais barato</span>' if vencedor else ""
    return f"""<article class="produto" id="produto-{e(p['apelido']).lower()}">
  {marca_rotulo}{foto(p)}
  <div class="corpo">
    <div class="selos">{selo}{coroa}</div>
    <h2>{e(p['nome'])}</h2>
    {estrelas}
    <div class="preco"><span class="agora numero">{reais(melhor_preco(p))}</span>{antes}</div>
    {f'<p class="explica {ds["tom"]}">{e(ds["texto"])}{". " + e(ds["extra"]) if ds["extra"] else ""}.</p>' if ds else ""}
    {indisponivel}
    <div class="lojas">{botoes}</div>
    <p class="aviso">Preço conferido em {dia(d['conferidoEm'])}. Pode mudar na loja.</p>
  </div>
</article>"""


def lista(itens, classe=""):
    return f'<ul class="{classe}">' + "".join(f"<li>{e(i)}</li>" for i in itens) + "</ul>"


# ---------- página do vídeo ----------

def pagina_video(d, todos):
    n = d["numero"]
    tit = titulo(d)
    desc = descricao(d)
    caminho = f"/{n}/"
    ps = produtos(d)
    partes = []

    if d["formato"] == "c2":
        a, b = d["a"], d["b"]
        mais_barato = "a" if melhor_preco(a) <= melhor_preco(b) else "b"
        placar = {"a": 0, "b": 0}
        for r in d["rodadas"]:
            if r["vence"] in placar:
                placar[r["vence"]] += 1
        resposta = f"""<div class="resposta cartao">
  <div class="sobrelinha">Resposta rápida</div>
  <div class="escolhas">
    <a class="escolha" href="#produto-a"><b>Vai na {e(a['apelido'])}</b> se você {e(d['seA'][0][0].lower() + d['seA'][0][1:])}</a>
    <a class="escolha" href="#produto-b"><b>Vai na {e(b['apelido'])}</b> se você {e(d['seB'][0][0].lower() + d['seB'][0][1:])}</a>
  </div>
</div>"""
        cartoes = (f'<div class="vs">{cartao_produto(a, d, "A", mais_barato == "a")}'
                   f'<span class="vs-marca" aria-hidden="true">VS</span>{cartao_produto(b, d, "B", mais_barato == "b")}</div>')
        linhas = "".join(
            f'<tr><th scope="row">{e(r["titulo"])}{f"<small>{e(r.get("dica", ""))}</small>" if r.get("dica") else ""}</th>'
            f'<td class="{"vence" if r["vence"] == "a" else ""}">{e(r["a"])}</td>'
            f'<td class="{"vence" if r["vence"] == "b" else ""}">{e(r["b"])}</td>'
            f'<td class="quem">{"Empate" if r["vence"] == "empate" else "Ponto para " + r["vence"].upper()}</td></tr>'
            for r in d["rodadas"])
        partes.append(f"""<section class="secao-p"><h2>Rodada por rodada</h2>
<div class="rolagem"><table class="placar">
<thead><tr><th></th><th scope="col">A</th><th scope="col">B</th><th scope="col">Quem leva</th></tr></thead>
<tbody>{linhas}</tbody>
<tfoot><tr><th scope="row">Placar</th><td class="numero">{placar['a']}</td><td class="numero">{placar['b']}</td><td></td></tr></tfoot>
</table></div></section>""")
        partes.append(f"""<section class="secao-p"><h2>O preço caiu de verdade?</h2>
<div class="graficos"><div><h3>{e(a['nome'])}</h3>{grafico(a)}<p class="explica {desconto(a)['tom'] if desconto(a) else ''}">{e(desconto(a)['texto']) if desconto(a) else ''}</p></div>
<div><h3>{e(b['nome'])}</h3>{grafico(b)}<p class="explica {desconto(b)['tom'] if desconto(b) else ''}">{e(desconto(b)['texto']) if desconto(b) else ''}</p></div></div></section>""")
        partes.append(f"""<section class="secao-p"><h2>Para quem é cada uma</h2>
<div class="colunas"><div class="lado sim"><b>Compre a {e(a['apelido'])} se</b>{lista(d['seA'])}</div>
<div class="lado sim"><b>Compre a {e(b['apelido'])} se</b>{lista(d['seB'])}</div></div></section>""")
        faq = [
            (f"Qual é melhor: {a['nome']} ou {b['nome']}?",
             f"Depende do uso. A {a['nome']} é melhor para quem {d['seA'][0].lower()}. A {b['nome']} é melhor para quem {d['seB'][0].lower()}. No nosso placar deu {placar['a']} a {placar['b']}."),
            (f"O desconto da {a['nome']} é real?", desconto(a)["texto"] + "." if desconto(a) else "Ainda não temos histórico suficiente."),
            (f"O desconto da {b['nome']} é real?", desconto(b)["texto"] + "." if desconto(b) else "Ainda não temos histórico suficiente."),
        ]
        fixo = "".join(f'<a href="{e(lojas_ordenadas(p)[0]["url"])}" rel="sponsored nofollow noopener" target="_blank">'
                       f'<span>{e(p["apelido"])}</span><b class="numero">{reais(melhor_preco(p))}</b></a>'
                       for p in ps if lojas_ordenadas(p))
    else:
        p = d["produto"]
        resposta = f"""<div class="resposta cartao">
  <div class="sobrelinha">Resposta rápida</div>
  <div class="colunas"><div class="lado sim"><b>Compre se</b>{lista(d['compreSe'])}</div>
  <div class="lado nao"><b>Não compre se</b>{lista(d['naoCompreSe'])}</div></div>
</div>"""
        cartoes = f'<div class="vs um">{cartao_produto(p, d)}</div>'
        partes.append(f"""<section class="secao-p"><h2>O preço caiu de verdade?</h2>{grafico(p)}
<p class="explica {desconto(p)['tom'] if desconto(p) else ''}">{e(desconto(p)['texto']) if desconto(p) else ''}</p></section>""")
        partes.append(f"""<section class="secao-p"><h2>O que dizem os compradores</h2>
<div class="colunas"><div class="lado sim"><b>Elogiam</b>{lista(d['bom'])}</div>
<div class="lado nao"><b>Reclamam</b>{lista(d['ruim'])}</div></div></section>""")
        faq = [
            (f"{p['nome']} vale a pena?", f"Vale para quem {d['compreSe'][0].lower()}. Não vale para quem {d['naoCompreSe'][0].lower()}."),
            ("O desconto é real?", desconto(p)["texto"] + "." if desconto(p) else "Ainda não temos histórico suficiente."),
            ("Qual o defeito mais citado?", f"{d['ruim'][0]}, segundo as avaliações dos compradores."),
        ]
        fixo = (f'<a href="{e(lojas_ordenadas(p)[0]["url"])}" rel="sponsored nofollow noopener" target="_blank">'
                f'<span>Melhor preço</span><b class="numero">{reais(melhor_preco(p))}</b></a>') if lojas_ordenadas(p) else ""

    video = ""
    if d.get("youtube"):
        video = (f'<section class="secao-p"><h2>Veja o vídeo</h2><div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{e(d["youtube"])}" '
                 f'title="{e(tit)}" loading="lazy" allow="encrypted-media; picture-in-picture" allowfullscreen></iframe></div></section>')
    partes.append(video)
    partes.append('<section class="secao-p"><h2>Perguntas frequentes</h2>' +
                  "".join(f"<details><summary>{e(q)}</summary><p>{e(r)}</p></details>" for q, r in faq) + "</section>")

    outros = [o for o in todos if o["numero"] != n][:3]
    if outros:
        partes.append('<section class="secao-p"><h2>Outras comparações</h2><div class="guias">' +
                      "".join(cartao_video(o) for o in outros) + "</div></section>")

    # dados estruturados: página, migalhas, produtos com ofertas, perguntas
    itens = []
    for p in ps:
        prod = {"@type": "Product", "name": p["nome"]}
        if p.get("foto"):
            prod["image"] = p["foto"]
        ofertas = [{"@type": "Offer", "price": f'{l["preco"]:.2f}', "priceCurrency": "BRL", "url": l["url"],
                    "availability": "https://schema.org/" + ("OutOfStock" if p.get("disponivel") is False else "InStock"),
                    "seller": {"@type": "Organization", "name": LOJAS.get(l["loja"], (l["loja"],))[0]}}
                   for l in lojas_ordenadas(p)]
        if ofertas:
            prod["offers"] = ofertas
        if d["formato"] == "c1":
            prod["review"] = {"@type": "Review", "author": {"@type": "Organization", "name": MARCA},
                              "positiveNotes": {"@type": "ItemList", "itemListElement": [
                                  {"@type": "ListItem", "position": i + 1, "name": t} for i, t in enumerate(d["bom"])]},
                              "negativeNotes": {"@type": "ItemList", "itemListElement": [
                                  {"@type": "ListItem", "position": i + 1, "name": t} for i, t in enumerate(d["ruim"])]}}
        itens.append(prod)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": SITE + caminho, "url": SITE + caminho, "name": tit, "description": desc,
         "inLanguage": "pt-BR", "datePublished": d["data"], "dateModified": d["conferidoEm"],
         "publisher": {"@id": SITE + "/#org"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": f"Nº {n}", "item": SITE + caminho}]},
        {"@type": "ItemList", "name": tit, "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": it} for i, it in enumerate(itens)]},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]},
    ]}

    gancho = " ".join(d.get("gancho", []))
    corpo = f"""<main id="conteudo" class="pagina-video"><div class="caixa">
<nav class="migalhas" aria-label="Você está em"><a href="/">Início</a><span aria-hidden="true">›</span><span>{e(d['categoria'])}</span><span aria-hidden="true">›</span><span>Nº {n}</span></nav>
<header class="titulo-video">
  <div class="sobrelinha"><span class="numero-video">Nº {n}</span> {e(d['categoria'])} · conferido em {dia(d['conferidoEm'])}</div>
  <h1>{e(tit)}</h1>
  {f'<p class="lead">{e(gancho)}</p>' if gancho else ''}
</header>
{resposta}
{cartoes}
{''.join(partes)}
<p class="aviso-final">Alguns links levam a lojas parceiras, e recebemos uma pequena comissão se você comprar por eles. O preço para você não muda. <a href="/transparencia.html">Como trabalhamos</a>.</p>
</div></main>
{f'<nav class="barra-fixa" aria-label="Comprar">{fixo}</nav>' if fixo else ''}
"""
    return cabeca(f"{tit} | {MARCA}", desc, caminho, json_ld(ld)) + corpo + rodape()


def cartao_video(d):
    ps = produtos(d)
    nomes = " ou ".join(p["nome"] for p in ps)
    precos = " · ".join(reais(melhor_preco(p)) for p in ps)
    ds = [desconto(p) for p in ps]
    selo = ""
    if any(x and x["tom"] == "ruim" for x in ds):
        selo = '<span class="selo ruim">Tem desconto de vitrine</span>'
    elif any(x and x["tom"] == "bom" for x in ds):
        selo = '<span class="selo bom">Desconto real</span>'
    fotos = "".join(foto(p, "foto") for p in ps)
    return f"""<a class="guia" href="/{d['numero']}/" data-numero="{d['numero']}" data-busca="{e((nomes + ' ' + d['categoria']).lower())}">
  <div class="fotos{' dupla' if len(ps) == 2 else ''}">{fotos}<span class="numero-video">Nº {d['numero']}</span></div>
  <div class="corpo">
    <div class="selos">{selo}</div>
    <h3>{e(titulo(d))}</h3>
    <p class="meta"><span class="numero">{precos}</span><span>{dia(d['conferidoEm'])}</span></p>
  </div>
</a>"""


# ---------- página inicial ----------

def pagina_inicial(todos):
    desc = ("Comparações curtas de eletroportáteis e utilidades da casa: qual comprar, se o desconto é real e para quem "
            "cada produto vale a pena. Viu um número no vídeo? Procure aqui.")
    if todos:
        cartoes = "".join(cartao_video(d) for d in todos)
        grade = f'<div class="guias" id="lista">{cartoes}</div><p class="vazio" id="nada" hidden>Nenhuma comparação com esse número ou nome.</p>'
    else:
        grade = '<p class="vazio">As primeiras comparações estão sendo conferidas e chegam em breve.</p>'
    numeros = [d["numero"] for d in todos]
    exemplo = f"Ex.: {todos[0]['numero']}" if todos else "Ex.: 12"

    vitrine = ""
    if todos:
        d = todos[0]
        ps = produtos(d)
        linhas = "".join(
            f'<div class="linha-vitrine">{foto(p, "mini")}<div><b>{e(p["nome"])}</b>'
            f'<span class="numero">{reais(melhor_preco(p))}</span></div>'
            f'{f"<span class=\"selo {desconto(p)["tom"]}\">{e(desconto(p)["curto"])}</span>" if desconto(p) else ""}</div>'
            for p in ps)
        vitrine = f"""<a class="cartao vitrine" href="/{d['numero']}/">
  <div class="cabeca"><span class="numero-video">Nº {d['numero']}</span><span class="tinta-3">Mais recente</span></div>
  {linhas}
  <span class="ver">Ver a comparação →</span>
</a>"""
    else:
        vitrine = """<div class="cartao vitrine" aria-hidden="true">
  <div class="cabeca"><span class="numero-video">Nº 1</span><span class="tinta-3">Assim fica cada comparação</span></div>
  <div class="linha-vitrine"><div class="mini sem-foto"></div><div><b>Produto A</b><span class="numero">R$ 289</span></div><span class="selo bom">−14% real</span></div>
  <div class="linha-vitrine"><div class="mini sem-foto"></div><div><b>Produto B</b><span class="numero">R$ 449</span></div><span class="selo ruim">Desconto de vitrine</span></div>
  <span class="ver">Preço, defeitos e para quem vale</span>
</div>"""

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": SITE + "/#org", "name": MARCA, "url": SITE + "/", "logo": SITE + "/og.png",
         "email": "compraconferida@gmail.com",
         "sameAs": ["https://www.youtube.com/@compraconferida", "https://www.tiktok.com/@compraconferida",
                    "https://www.instagram.com/compraconferida", "https://br.pinterest.com/compraconferida"]},
        {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": MARCA, "inLanguage": "pt-BR",
         "publisher": {"@id": SITE + "/#org"}},
    ]}
    if todos:
        ld["@graph"].append({"@type": "ItemList", "name": "Comparações", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": f"{SITE}/{d['numero']}/", "name": titulo(d)} for i, d in enumerate(todos)]})

    script = f"""<script>
(() => {{
  const numeros = new Set({json.dumps(numeros)});
  const form = document.getElementById('procura'), campo = document.getElementById('campo');
  const cartoes = [...document.querySelectorAll('#lista .guia')], nada = document.getElementById('nada'), msg = document.getElementById('msg');
  const filtrar = () => {{
    const q = campo.value.trim().toLowerCase().replace(/^n[ºo°]?\\s*/, '');
    let vis = 0;
    cartoes.forEach(c => {{ const ok = !q || c.dataset.numero === q || c.dataset.busca.includes(q); c.hidden = !ok; vis += ok; }});
    if (nada) nada.hidden = vis > 0;
    msg.textContent = '';
  }};
  campo.addEventListener('input', filtrar);
  form.addEventListener('submit', ev => {{
    ev.preventDefault();
    const n = parseInt(campo.value.replace(/\\D/g, ''), 10);
    if (numeros.has(n)) location.href = '/' + n + '/';
    else {{ msg.textContent = isNaN(n) ? 'Digite o número que aparece no vídeo.' : 'O nº ' + n + ' ainda não está no ar. Veja a lista abaixo.'; document.getElementById('comparacoes').scrollIntoView({{behavior: 'smooth'}}); }}
  }});
}})();
</script>
"""

    corpo = f"""<main id="conteudo">
<section class="abertura"><div class="caixa">
  <div>
    <div class="sobrelinha">Guia de compra independente</div>
    <h1>Antes de comprar, <span class="marca-texto">a gente confere.</span></h1>
    <p class="lead">Dois produtos lado a lado, o preço de hoje contra o de sempre e para quem cada um vale a pena. Em um minuto.</p>
    <form class="procura" id="procura" role="search" action="/" autocomplete="off">
      <label for="campo">Viu um número no vídeo? Procure aqui</label>
      <div class="campo-linha"><span class="prefixo">Nº</span><input id="campo" name="n" inputmode="numeric" placeholder="{exemplo}" aria-describedby="msg"><button class="botao" type="submit">Abrir</button></div>
      <p class="msg" id="msg" role="status"></p>
    </form>
  </div>
  {vitrine}
</div></section>

<section class="confianca"><div class="caixa">
  <div><b>Preço acompanhado</b><span>todo dia, para pegar desconto de vitrine</span></div>
  <div><b>Avaliações reais</b><span>defeitos que se repetem, não casos isolados</span></div>
  <div><b>Sem produto de graça</b><span>ninguém paga pelo veredito</span></div>
</div></section>

<section class="secao" id="comparacoes"><div class="caixa">
  <div class="sobrelinha">Comparações</div>
  <h2>Da mais nova para a mais antiga</h2>
  {grade}
</div></section>

<section class="secao" id="como"><div class="caixa">
  <div class="sobrelinha">Como conferimos</div>
  <h2 class="texto">Três perguntas antes de qualquer veredito.</h2>
  <div class="passos">
    <div class="passo"><div class="icone"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
      <h3>O que dizem os compradores?</h3><p>Contamos os defeitos e elogios que mais se repetem nas avaliações. Um caso isolado não vira regra.</p></div>
    <div class="passo"><div class="icone"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/></svg></div>
      <h3>O preço caiu de verdade?</h3><p>Comparamos o preço de hoje com o preço de sempre. Desconto de vitrine não passa.</p></div>
    <div class="passo"><div class="icone"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
      <h3>Para quem vale a pena?</h3><p>Toda comparação termina em "compre se". Às vezes a melhor compra é a mais barata, às vezes não.</p></div>
  </div>
</div></section>

<section class="secao"><div class="caixa texto">
  <div class="sobrelinha">Como ganhamos dinheiro</div>
  <p class="lead">Alguns links levam a lojas parceiras, e recebemos uma pequena comissão se você comprar por eles. O preço para você não muda, e a loja mais barata aparece sempre primeiro. <a href="/transparencia.html">Detalhes em Transparência</a>.</p>
</div></section>
</main>
"""
    tit = f"{MARCA}: qual comprar? Comparações com preço conferido"
    return cabeca(tit, desc, "/", json_ld(ld)) + corpo + rodape(script)


def pagina_texto(nome):
    bruto = (RAIZ / "fonte" / f"{nome}.html").read_text(encoding="utf-8")
    meta = {}
    for linha in bruto.splitlines():
        if linha.startswith("<!-- ") and ":" in linha:
            k, v = linha[5:-4].split(":", 1)
            meta[k.strip()] = v.strip()
    conteudo = "\n".join(l for l in bruto.splitlines() if not l.startswith("<!-- "))
    return (cabeca(f"{meta['titulo']} | {MARCA}", meta["descricao"], f"/{nome}.html") +
            f'<main id="conteudo" class="artigo"><div class="caixa texto">\n{conteudo}\n</div></main>\n' + rodape())


def pagina_404():
    return (cabeca(f"Página não encontrada | {MARCA}", "Essa página não existe.", "/404.html",
                   '<meta name="robots" content="noindex">\n') +
            '<main id="conteudo" class="artigo"><div class="caixa texto"><div class="sobrelinha">Erro 404</div>'
            '<h1>Essa página não existe.</h1><p class="lead">Se você veio de um vídeo, procure o número dele na página inicial.</p>'
            '<p><a class="botao" href="/">Ir para as comparações</a></p></div></main>\n' + rodape())


# ---------- montagem ----------

def carregar(previa):
    pastas = [RAIZ / "dados"] + ([RAIZ / "dados" / "exemplos"] if previa else [])
    todos = []
    for pasta in pastas:
        for f in sorted(pasta.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("exemplo") and not previa:
                sys.exit(f"{f.name} está marcado como exemplo: não pode ser publicado.")
            todos.append(d)
    vistos = set()
    for d in todos:
        if d["numero"] in vistos:
            sys.exit(f"Número repetido: {d['numero']}")
        vistos.add(d["numero"])
    return sorted(todos, key=lambda d: d["numero"], reverse=True)


def main():
    previa = "--previa" in sys.argv
    saida = RAIZ.parent / "previa-site" if previa else RAIZ
    if previa:
        if saida.exists():
            shutil.rmtree(saida)
        saida.mkdir()
        for nome in ESTATICOS:
            if (RAIZ / nome).exists():
                shutil.copy2(RAIZ / nome, saida / nome)
    else:
        # some com as páginas de vídeos que saíram dos dados
        for pasta in RAIZ.iterdir():
            if pasta.is_dir() and pasta.name.isdigit() and not (RAIZ / "dados" / f"{pasta.name}.json").exists():
                shutil.rmtree(pasta)

    todos = carregar(previa)
    escrever = lambda caminho, texto: (saida / caminho).parent.mkdir(parents=True, exist_ok=True) or \
        (saida / caminho).write_text(texto, encoding="utf-8", newline="\n")

    escrever("index.html", pagina_inicial(todos))
    for d in todos:
        escrever(f"{d['numero']}/index.html", pagina_video(d, todos))
    for nome in ("transparencia", "privacidade"):
        escrever(f"{nome}.html", pagina_texto(nome))
    escrever("404.html", pagina_404())

    hoje = date.today().isoformat()
    urls = [("/", max([d["conferidoEm"] for d in todos], default=hoje))]
    urls += [(f"/{d['numero']}/", d["conferidoEm"]) for d in todos]
    urls += [("/transparencia.html", hoje), ("/privacidade.html", hoje)]
    escrever("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
             "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{m}</lastmod></url>\n" for u, m in urls) + "</urlset>\n")
    escrever("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /dados/\nDisallow: /fonte/\n\nSitemap: {SITE}/sitemap.xml\n")
    print(f"{len(todos)} comparacao(oes) -> {saida}")


if __name__ == "__main__":
    main()

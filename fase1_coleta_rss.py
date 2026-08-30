"""
MÓDULO: Fase 1 - Coleta e Mineração de Dados (RSS Feeds - Multicanais)
OBJETIVO: Ler múltiplas fontes de notícias públicas simultaneamente, extrair dados
          estruturados (título, link, imagem e nome_fonte) e consolidar em uma única
          lista unificada para a Fase 2 processar com IA.
"""

import re
import sys
from typing import Any

import feedparser

# Garante suporte a caracteres UTF-8 no terminal do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Dicionário multicanal: chave -> (nome_exibição, url_rss)
FEEDS_CONFIG: dict[str, tuple[str, str]] = {
    "g1_tecnologia":  ("G1",           "https://g1.globo.com/rss/g1/tecnologia/"),
    "g1_brasil":      ("G1",           "https://g1.globo.com/rss/g1/brasil/"),
    "canaltech":      ("Canaltech",    "https://canaltech.com.br/rss/"),
    "tecmundo":       ("TecMundo",     "https://rss.tecmundo.com.br/feed"),
    "olhar_digital":  ("Olhar Digital","https://olhardigital.com.br/feed/"),
    "techtudo":       ("TechTudo",     "https://www.techtudo.com.br/rss/"),
    "bbc_brasil":     ("BBC Brasil",   "https://feeds.bbci.co.uk/portuguese/rss.xml"),
}


def extrair_imagem_rss(entrada: Any) -> str | None:
    """
    Extrai a URL da imagem oficial/thumbnail da matéria a partir de múltiplos atributos comuns
    do XML RSS/Atom fornecidos pelo feedparser.

    Ordem de busca segura:
    1. entrada.media_content: lista de mídias estruturadas (ex: G1, Reuters)
    2. entrada.media_thumbnail: thumbnails oficiais (ex: BBC, CNN)
    3. entrada.enclosures: anexos de mídia padrão RSS 2.0
    4. entrada.links: links com rel="enclosure" ou type iniciando com "image/"
    5. Regex em entrada.summary ou entrada.description: captura tags <img src="...">

    Args:
        entrada (Any): Objeto FeedParserDict representando uma entrada do feed.

    Returns:
        Optional[str]: URL absoluta da imagem encontrada ou None se não localizada.
    """
    # 1. media_content (ex: G1, Yahoo, Reuters)
    media_content = entrada.get("media_content")
    if isinstance(media_content, list) and len(media_content) > 0:
        for media in media_content:
            if isinstance(media, dict):
                url = media.get("url")
                medium = media.get("medium", "")
                tipo = media.get("type", "")
                if url and (
                    medium == "image" or tipo.startswith("image/") or not medium
                ):
                    return url.strip()

    # 2. media_thumbnail (ex: BBC, canais internacionais)
    media_thumbnail = entrada.get("media_thumbnail")
    if isinstance(media_thumbnail, list) and len(media_thumbnail) > 0:
        for thumb in media_thumbnail:
            if isinstance(thumb, dict) and thumb.get("url"):
                return thumb["url"].strip()

    # 3. enclosures (anexos RSS 2.0)
    enclosures = entrada.get("enclosures")
    if isinstance(enclosures, list) and len(enclosures) > 0:
        for enc in enclosures:
            if isinstance(enc, dict):
                url = enc.get("href") or enc.get("url")
                tipo = enc.get("type", "")
                if url:
                    extensoes_imagem = (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".gif",
                        ".svg",
                    )
                    if tipo.startswith("image/") or any(
                        url.lower().endswith(ext) for ext in extensoes_imagem
                    ):
                        return url.strip()

    # 4. links (rel="enclosure" ou type="image/*")
    links = entrada.get("links")
    if isinstance(links, list) and len(links) > 0:
        for link in links:
            if isinstance(link, dict):
                rel = link.get("rel", "")
                tipo = link.get("type", "")
                href = link.get("href", "")
                if href and (rel == "enclosure" or tipo.startswith("image/")):
                    return href.strip()

    # 5. Regex de busca em summary, description ou content (<img src="...">)
    for campo in ["summary", "description", "content"]:
        conteudo = entrada.get(campo)
        if isinstance(conteudo, list) and len(conteudo) > 0:
            primeiro = conteudo[0]
            conteudo = (
                primeiro.get("value", "")
                if isinstance(primeiro, dict)
                else str(primeiro)
            )

        if isinstance(conteudo, str) and conteudo:
            match = re.search(
                r'<img[^>]+src=["\'](https?://[^"\'<>]+)["\']', conteudo, re.IGNORECASE
            )
            if match:
                return match.group(1).strip()

    return None


def coletar_noticias_rss(
    url_feed: str,
    nome_fonte: str,
    limite: int = 5,
) -> list[dict[str, str | None]]:
    """
    Lê um feed RSS a partir de uma URL e extrai as notícias mais recentes com título,
    link da matéria, imagem oficial e nome rastreável da fonte.

    Args:
        url_feed (str): Endereço URL do feed RSS.
        nome_fonte (str): Nome legível da fonte (ex: 'G1', 'TecMundo').
        limite (int): Quantidade máxima de notícias a serem extraídas.

    Returns:
        List[Dict[str, Optional[str]]]: Lista de dicionários com 'titulo', 'link',
        'imagem_url' e 'nome_fonte'.
    """
    print(f"[+] [{nome_fonte}] Conectando ao feed: {url_feed}...")

    try:
        feed = feedparser.parse(url_feed)
    except Exception as e:
        print(f"[!] [{nome_fonte}] Falha ao conectar ao feed: {e}")
        return []

    if feed.bozo:
        print(f"[!] [{nome_fonte}] Aviso: Possível inconsistência no feed ({feed.bozo_exception})")

    noticias_coletadas = []

    for entrada in feed.entries[:limite]:
        titulo = entrada.get("title", "Título não disponível").strip()
        link = entrada.get("link", "Link não disponível").strip()
        imagem_url = extrair_imagem_rss(entrada)

        noticias_coletadas.append({
            "titulo":     titulo,
            "link":       link,
            "imagem_url": imagem_url,
            "nome_fonte": nome_fonte,
        })

    print(f"  [✓] [{nome_fonte}] {len(noticias_coletadas)} notícia(s) coletada(s).")
    return noticias_coletadas


def coletar_todos_os_feeds(
    feeds: dict[str, tuple[str, str]] | None = None,
    limite_por_fonte: int = 3,
) -> list[dict[str, str | None]]:
    """
    Itera sobre todas as fontes configuradas em FEEDS_CONFIG, coleta as notícias de
    cada uma e consolida em uma única lista unificada com rastreabilidade de origem.

    Args:
        feeds (dict | None): Dicionário de feeds a usar. Se None, usa FEEDS_CONFIG completo.
        limite_por_fonte (int): Máximo de notícias a coletar por fonte.

    Returns:
        List[Dict]: Lista unificada de notícias de todas as fontes, com 'nome_fonte'.
    """
    feeds_alvo = feeds or FEEDS_CONFIG
    lista_unificada: list[dict[str, str | None]] = []

    print(f"\n[+] Iniciando coleta multicanal: {len(feeds_alvo)} fonte(s) configurada(s).")
    print(f"    Limite por fonte: {limite_por_fonte} notícia(s).\n")

    for chave, (nome, url) in feeds_alvo.items():
        noticias = coletar_noticias_rss(url_feed=url, nome_fonte=nome, limite=limite_por_fonte)
        lista_unificada.extend(noticias)

    print(f"\n[✓] Coleta multicanal concluída: {len(lista_unificada)} notícia(s) no total.\n")
    return lista_unificada


def exibir_no_terminal(noticias: list[dict[str, str | None]]) -> None:
    """
    Exibe os dados minerados no terminal de forma legível com título, fonte, link e imagem.
    """
    print("\n" + "=" * 80)
    print(f" RESULTADOS DA MINERAÇÃO MULTICANAL - {len(noticias)} NOTÍCIA(S) COLETADA(S)")
    print("=" * 80)

    if not noticias:
        print("[!] Nenhuma notícia encontrada.")
        return

    for indice, item in enumerate(noticias, start=1):
        fonte = item.get("nome_fonte", "Desconhecida")
        print(f"\n[{indice:02d}] [{fonte}] {item['titulo']}")
        print(f"      Link  : {item['link']}")
        img_display = (
            item["imagem_url"]
            if item.get("imagem_url")
            else "[Nenhuma imagem oficial localizada]"
        )
        print(f"      Imagem: {img_display}")

    print("\n" + "=" * 80)
    print(f"[OK] Total extraído: {len(noticias)} notícia(s) de {len(set(n.get('nome_fonte') for n in noticias))} fonte(s)")
    print("=" * 80 + "\n")


def main():
    """
    Fluxo principal de execução da Fase 1 — modo multicanal completo.
    """
    noticias = coletar_todos_os_feeds(limite_por_fonte=3)
    exibir_no_terminal(noticias)


if __name__ == "__main__":
    main()

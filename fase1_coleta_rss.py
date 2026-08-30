"""
MÓDULO: Fase 1 - Coleta e Mineração de Dados (RSS Feeds)
OBJETIVO: Ler fontes de notícias públicas, extrair dados estruturados (título, link e imagem oficial)
          e exibir de forma limpa no terminal sem sobrecarregar a máquina.
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

# Dicionário com feeds RSS confiáveis para teste
FEEDS_CONFIG = {
    "g1_brasil": "https://g1.globo.com/rss/g1/brasil/",
    "g1_tecnologia": "https://g1.globo.com/rss/g1/tecnologia/",
    "bbc_brasil": "https://feeds.bbci.co.uk/portuguese/rss.xml",
    "agencia_brasil": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
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
                r'<img[^>]+src=["\'](https?://[^"\'>]+)["\']', conteudo, re.IGNORECASE
            )
            if match:
                return match.group(1).strip()

    return None


def coletar_noticias_rss(url_feed: str, limite: int = 5) -> list[dict[str, str | None]]:
    """
    Lê um feed RSS a partir de uma URL e extrai as notícias mais recentes com título,
    link da matéria e imagem oficial.

    Args:
        url_feed (str): Endereço URL do feed RSS.
        limite (int): Quantidade máxima de notícias a serem extraídas.

    Returns:
        List[Dict[str, Optional[str]]]: Lista de dicionários contendo 'titulo', 'link' e 'imagem_url'.
    """
    print(f"[+] Conectando ao feed: {url_feed}...")

    # Faz o download e o parsing estrutural do XML do feed
    feed = feedparser.parse(url_feed)

    # Verificação básica de integridade da resposta
    if feed.bozo:
        print(f"[!] Aviso: Possível inconsistência no feed ({feed.bozo_exception})")

    noticias_coletadas = []

    # Itera sobre as entradas do feed respeitando o limite definido
    for entrada in feed.entries[:limite]:
        titulo = entrada.get("title", "Título não disponível").strip()
        link = entrada.get("link", "Link não disponível").strip()

        # Extração resiliente da imagem oficial embutida no XML
        imagem_url = extrair_imagem_rss(entrada)

        noticias_coletadas.append(
            {"titulo": titulo, "link": link, "imagem_url": imagem_url}
        )

    return noticias_coletadas


def exibir_no_terminal(noticias: list[dict[str, str | None]], fonte_nome: str) -> None:
    """
    Exibe os dados minerados no terminal de forma legível com título, link e imagem.
    """
    print("\n" + "=" * 80)
    print(f" RESULTADOS DA MINERAÇÃO - FONTE: {fonte_nome.upper()}")
    print("=" * 80)

    if not noticias:
        print("[!] Nenhuma notícia encontrada.")
        return

    for indice, item in enumerate(noticias, start=1):
        print(f"\n[{indice}] Título: {item['titulo']}")
        print(f"    Link  : {item['link']}")
        img_display = (
            item["imagem_url"]
            if item.get("imagem_url")
            else "[Nenhuma imagem oficial localizada]"
        )
        print(f"    Imagem: {img_display}")

    print("\n" + "=" * 80)
    print(f"[OK] Total extraído com sucesso: {len(noticias)} notícia(s)")
    print("=" * 80 + "\n")


def main():
    """
    Fluxo principal de execução da Fase 1.
    """
    feed_escolhido = "g1_tecnologia"
    url = FEEDS_CONFIG[feed_escolhido]

    # Executa a extração
    noticias = coletar_noticias_rss(url_feed=url, limite=5)

    # Exibe os resultados completos no terminal
    exibir_no_terminal(noticias, fonte_nome=feed_escolhido)


if __name__ == "__main__":
    main()

"""
MÓDULO: Fase 1 - Coleta e Mineração de Dados (RSS Feeds)
OBJETIVO: Ler fontes de notícias públicas, extrair dados estruturados (título e link)
          e exibir de forma limpa no terminal sem sobrecarregar a máquina.
"""

import sys

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


def coletar_noticias_rss(url_feed: str, limite: int = 5) -> list[dict[str, str]]:
    """
    Lê um feed RSS a partir de uma URL e extrai as notícias mais recentes.

    Args:
        url_feed (str): Endereço URL do feed RSS.
        limite (int): Quantidade máxima de notícias a serem extraídas.

    Returns:
        List[Dict[str, str]]: Lista de dicionários contendo 'titulo' e 'link'.
    """
    print(f"[+] Conectando ao feed: {url_feed}...")

    # Faz o download e o parsing (análise estrutural) do XML do feed
    feed = feedparser.parse(url_feed)

    # Verificação básica de integridade da resposta
    if feed.bozo:
        # 'bozo' é um indicador do feedparser para problemas no XML ou na conexão
        print(f"[!] Aviso: Possível inconsistência no feed ({feed.bozo_exception})")

    noticias_coletadas = []

    # Itera sobre as entradas do feed respeitando o limite definido
    for entrada in feed.entries[:limite]:
        titulo = entrada.get("title", "Título não disponível").strip()
        link = entrada.get("link", "Link não disponível").strip()

        noticias_coletadas.append({"titulo": titulo, "link": link})

    return noticias_coletadas


def exibir_no_terminal(noticias: list[dict[str, str]], fonte_nome: str) -> None:
    """
    Exibe os dados minerados no terminal de forma legível.
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

    print("\n" + "=" * 80)
    print(f"[OK] Total extraído com sucesso: {len(noticias)} notícia(s)")
    print("=" * 80 + "\n")


def main():
    """
    Fluxo principal de execução.
    """
    # 1. Escolha qual feed deseja testar
    feed_escolhido = "g1_tecnologia"
    url = FEEDS_CONFIG[feed_escolhido]

    # 2. Executa a extração (modular e independente)
    # Pegamos apenas 5 notícias para teste rápido
    noticias = coletar_noticias_rss(url_feed=url, limite=5)

    # 3. Exibe os resultados
    exibir_no_terminal(noticias, fonte_nome=feed_escolhido)


# Garante que o script só rode quando executado diretamente
if __name__ == "__main__":
    main()

"""
MÓDULO: Fase 3 - Mídia Visual e Exportação (Markdown CMS)
OBJETIVO: Receber as notícias curadas pela IA na Fase 2, associar imagens ilustrativas
          dinâmicas e salvar cada matéria em um arquivo .md estruturado e pronto para CMS.
          Utiliza a biblioteca pathlib com tratamento de permissões e erros do Windows.
"""

import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

# Garante suporte a caracteres UTF-8 no terminal do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Importa o fluxo orquestrador da Fase 2
from fase2_geracao_ia import processar_fluxo_completo


def garantir_diretorio_exportacao(nome_pasta: str = "noticias_prontas") -> Path:
    """
    Verifica se a pasta de destino existe a partir do diretório de execução atual (CWD);
    caso contrário, cria-a automaticamente. Se houver restrições de permissão do sistema
    operacional (ex: WinError 2), captura o erro e orienta o usuário de forma limpa.

    Args:
        nome_pasta (str): Nome do diretório para salvar os arquivos Markdown.

    Returns:
        Path: Objeto Path do diretório garantido e pronto para uso.
    """
    pasta_destino = Path.cwd() / nome_pasta

    try:
        pasta_destino.mkdir(parents=True, exist_ok=True)
    except Exception:
        print("\n" + "!" * 80)
        print(
            f"[AVISO DE PERMISSÃO] O sistema operacional impediu a criação automática da pasta '{nome_pasta}'."
        )
        print(f"Caminho esperado: {pasta_destino.resolve()}")
        print(
            "Solução rápida: Crie uma pasta chamada 'noticias_prontas' manualmente neste diretório e tente novamente."
        )
        print("!" * 80 + "\n")
        sys.exit(0)

    return pasta_destino


def sanitizar_nome_arquivo(texto: str, max_caracteres: int = 50) -> str:
    """
    Converte um título em um slug limpo para nome de arquivo:
    - Converte para minúsculas;
    - Remove acentos e caracteres especiais;
    - Substitui espaços por hifens.

    Args:
        texto (str): Título original ou curado.
        max_caracteres (int): Comprimento máximo do nome do arquivo.

    Returns:
        str: Nome de arquivo sanitizado (slug) sem extensão.
    """
    # 1. Normaliza e remove acentos
    texto_sem_acento = (
        unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    )

    # 2. Converte para minúsculas e remove caracteres que não sejam letras, números ou espaços
    texto_limpo = re.sub(r"[^a-zA-Z0-9\s-]", "", texto_sem_acento).lower().strip()

    # 3. Substitui múltiplos espaços ou underscores por um único hífen
    slug = re.sub(r"[\s_]+", "-", texto_limpo)

    # Limita o tamanho para evitar nomes de arquivos excessivamente longos
    slug = slug[:max_caracteres].rstrip("-")

    return slug or "noticia"


def gerar_conteudo_markdown(artigo: dict[str, Any], slug: str) -> str:
    """
    Monta a estrutura interna do arquivo Markdown com Título, Imagem Oficial (Fase 1/2),
    Resumo da Notícia, Pontos Principais (bullets) e Impacto.

    Args:
        artigo (Dict[str, Any]): Dados da notícia curada pela IA com estrutura rica.
        slug (str): Identificador único usado para sanitização e fallback.

    Returns:
        str: Conteúdo formatado em Markdown pronto para o CMS.
    """
    titulo = artigo.get("titulo_curado", "Sem Título")
    resumo = artigo.get("resumo", "Sem Resumo disponível.")
    pontos_principais = artigo.get("pontos_principais", [])
    impacto = artigo.get("impacto", "Acompanhe as atualizações nos canais oficiais.")
    link_fonte = artigo.get("link", "#")

    # Injeta a imagem_url oficial extraída das Fases 1/2 (com fallback seguro caso não haja foto)
    url_imagem = (
        artigo.get("imagem_url") or f"https://picsum.photos/seed/{slug}/800/400"
    )

    # Renderiza a lista de pontos principais em bullet points markdown
    if isinstance(pontos_principais, list) and len(pontos_principais) > 0:
        bullets_md = "\n".join(
            f"- {ponto.strip()}" for ponto in pontos_principais if ponto.strip()
        )
    else:
        bullets_md = "- Acompanhe a cobertura dos desdobramentos na matéria original."

    secao_impacto = (
        impacto.strip()
        if impacto
        else "Para mais detalhes e análises sobre o impacto, consulte a matéria completa na íntegra."
    )

    template_markdown = f"""# {titulo}

![Imagem Ilustrativa]({url_imagem})

## Resumo da Notícia

{resumo}

## Pontos Principais

{bullets_md}

## Impacto

{secao_impacto}

---

🔗 **Fonte Original:** [Acesse a matéria completa na íntegra no portal oficial]({link_fonte})

*Publicado automaticamente via Pipeline de Curadoria com Inteligência Artificial.*
"""
    return template_markdown.strip()


def exportar_noticias_para_markdown(
    artigos: list[dict[str, Any]], pasta_destino: str = "noticias_prontas"
) -> list[Path]:
    """
    Salva cada notícia em um arquivo .md individual dentro da pasta indicada usando pathlib.

    Args:
        artigos (List[Dict[str, str]]): Lista de notícias curadas.
        pasta_destino (str): Nome da pasta onde os arquivos serão salvos.

    Returns:
        List[Path]: Lista com os objetos Path dos arquivos criados.
    """
    caminho_pasta = garantir_diretorio_exportacao(pasta_destino)
    arquivos_criados = []

    print(f"\n[+] Exportando artigos para a pasta: {caminho_pasta.resolve()}...\n")

    for idx, artigo in enumerate(artigos, start=1):
        titulo_base = artigo.get("titulo_curado", f"noticia_{idx}")
        slug = sanitizar_nome_arquivo(titulo_base)
        nome_arquivo = f"{slug}.md"
        caminho_arquivo = caminho_pasta / nome_arquivo

        conteudo_md = gerar_conteudo_markdown(artigo, slug)

        try:
            # Salva o arquivo em UTF-8 usando pathlib
            caminho_arquivo.write_text(conteudo_md, encoding="utf-8")
            arquivos_criados.append(caminho_arquivo)
            print(f"  [✓] Salvo ({idx}/{len(artigos)}): {nome_arquivo}")
        except Exception as err:
            print(f"  [!] Falha ao gravar '{nome_arquivo}': {err}")

    return arquivos_criados


def executar_fase3():
    """
    Fluxo principal da Fase 3: Executa o pipeline completo e exporta os arquivos Markdown.
    """
    print("\n" + "=" * 80)
    print(" INICIANDO PIPELINE: FASE 1 -> FASE 2 -> FASE 3 (EXPORTAÇÃO MARKDOWN)")
    print("=" * 80)

    # 1. Executa a Fase 1 (Coleta) + Fase 2 (Curadoria com Gemini via JSON Estruturado)
    artigos_curados = processar_fluxo_completo(
        limite_noticias=3, feed_chave="g1_tecnologia"
    )

    if not artigos_curados:
        print("[!] Nenhum artigo retornado para exportação.")
        return

    # 2. Executa a Fase 3 (Exportação para Markdown na pasta noticias_prontas via pathlib)
    arquivos = exportar_noticias_para_markdown(artigos_curados)

    print("\n" + "=" * 80)
    print(
        f"[OK] Fase 3 concluída com sucesso! {len(arquivos)} arquivo(s) .md gerado(s)."
    )
    print(f"     Diretório: {garantir_diretorio_exportacao().resolve()}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    executar_fase3()

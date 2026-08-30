"""
MÓDULO: Fase 2 - Curadoria e Geração com IA (Google Gemini API)
OBJETIVO: Processar os dados brutos minerados pela Fase 1 (multicanal) utilizando o modelo Gemini
          com saída forçada em JSON estruturado (application/json) e higienização defensiva de strings.
          Inclui sistema anticota (cache local em historico_urls.json) e mecanismo de retry resiliente.
          Suporta lista unificada de múltiplas fontes com rastreabilidade via campo 'nome_fonte'.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

# Garante suporte a caracteres UTF-8 no terminal do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Importa os extratores modulares da Fase 1
from fase1_coleta_rss import FEEDS_CONFIG, coletar_todos_os_feeds


def carregar_historico(caminho_arquivo: str = "historico_urls.json") -> list[str]:
    """
    Lê o arquivo historico_urls.json na raiz do projeto utilizando a biblioteca nativa json.
    Retorna a lista de links já processados. Se o arquivo não existir ou for inválido, retorna lista vazia.

    Args:
        caminho_arquivo (str): Nome ou caminho do arquivo JSON de histórico.

    Returns:
        List[str]: Lista de URLs já registradas.
    """
    caminho = Path(caminho_arquivo)
    if not caminho.exists():
        return []

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            if isinstance(dados, list):
                return dados
            return []
    except Exception as e:
        print(
            f"[!] Aviso: Não foi possível ler '{caminho_arquivo}' ({e}). Iniciando com histórico vazio."
        )
        return []


def salvar_historico(
    novas_urls: list[str], caminho_arquivo: str = "historico_urls.json"
) -> None:
    """
    Carrega o histórico atual, adiciona os novos links sem duplicatas e salva o arquivo
    historico_urls.json atualizado na raiz do projeto.

    Args:
        novas_urls (List[str]): Lista de URLs recém-processadas para gravar no histórico.
        caminho_arquivo (str): Nome ou caminho do arquivo JSON de histórico.
    """
    if not novas_urls:
        return

    caminho = Path(caminho_arquivo)
    historico_atual = carregar_historico(caminho_arquivo)

    # Mantém a unicidade preservando a ordem de inserção
    urls_existentes = set(historico_atual)
    adicionadas = 0

    for url in novas_urls:
        url_limpa = url.strip()
        if url_limpa and url_limpa not in urls_existentes:
            historico_atual.append(url_limpa)
            urls_existentes.add(url_limpa)
            adicionadas += 1

    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(historico_atual, f, indent=2, ensure_ascii=False)
        print(
            f"[✓] Histórico atualizado: {adicionadas} nova(s) URL(s) salva(s) em '{caminho.name}'. Total no cache: {len(historico_atual)}."
        )
    except Exception as e:
        print(f"[!] Erro ao salvar histórico de URLs em '{caminho.name}': {e}")


def obter_cliente_gemini() -> genai.Client:
    """
    Valida a existência da variável de ambiente GEMINI_API_KEY e instancia o cliente oficial.

    Returns:
        genai.Client: Instância autenticada do cliente Google GenAI.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("\n" + "!" * 80)
        print(
            "[ERRO DE SEGURANÇA] Variável de ambiente 'GEMINI_API_KEY' não encontrada!"
        )
        print("Para proteger sua credencial, nunca insira a chave direto no código.")
        print('Configure no PowerShell com: $env:GEMINI_API_KEY="sua_chave_aqui"')
        print("!" * 80 + "\n")
        sys.exit(1)

    return genai.Client(api_key=api_key)


def curar_noticia_com_ia(
    cliente: genai.Client,
    titulo_original: str,
    link_original: str,
    nome_fonte: str = "Desconhecida",
    imagem_url: str | None = None,
    modelo: str = "gemini-3.6-flash",
    max_tentativas: int = 3,
    intervalo_retry: int = 10,
) -> dict[str, Any]:
    """
    Envia a notícia bruta para o Google Gemini gerar uma versão curada por IA utilizando
    saída em JSON estruturado com 4 chaves estritas: titulo_curado, resumo, pontos_principais e impacto.

    Args:
        cliente (genai.Client): Cliente autenticado da API.
        titulo_original (str): Manchete original extraída do RSS.
        link_original (str): Link da matéria original.
        nome_fonte (str): Nome rastreável da fonte de origem (ex: 'G1', 'TecMundo').
        imagem_url (Optional[str]): URL da foto oficial extraída no RSS (Fase 1).
        modelo (str): Identificador do modelo leve na API do Google (padrão: gemini-3.6-flash).
        max_tentativas (int): Quantidade máxima de tentativas em caso de instabilidade.
        intervalo_retry (int): Tempo de espera em segundos para erros temporários (503).

    Returns:
        Dict[str, Any]: Dicionário contendo título curado, resumo, pontos principais, impacto,
        link, imagem e nome_fonte.
    """
    system_instruction = (
        "Você é um jornalista sênior, ético e imparcial em um portal de notícias de tecnologia e atualidades.\n"
        "Sua resposta deve ser ESTRITAMENTE um objeto JSON válido contendo exatamente as quatro chaves a seguir:\n"
        "- 'titulo_curado': string com um novo título profissional, claro, impactante e atrativo (sem sensacionalismo/clickbait).\n"
        "- 'resumo': string com um parágrafo conciso (3 a 4 frases) seguindo a estrutura de pirâmide invertida (foco em quem, o que e contexto), em tom neutro e formal.\n"
        "- 'pontos_principais': lista de exatamente 3 strings curtas e diretas com os tópicos/destaques mais relevantes da matéria (bullet points).\n"
        "- 'impacto': string com 1 a 2 frases destacando a conclusão, impacto prático no mercado/sociedade ou perspectivas futuras do fato.\n"
        "Não adicione comentários, textos adicionais ou blocos markdown fora do JSON."
    )

    mensagem_usuario = f"""
Com base exclusivamente no fato apresentado no título original abaixo, gere o JSON estruturado:

Título Original: "{titulo_original}"
Link da Fonte: {link_original}
"""

    for tentativa in range(1, max_tentativas + 1):
        try:
            # Força saída em JSON com limite ampliado de 1000 tokens para evitar cortes de texto
            chat = cliente.chats.create(
                model=modelo,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                    max_output_tokens=1000,
                    response_mime_type="application/json",
                ),
            )

            resposta = chat.send_message(mensagem_usuario)
            texto_bruto = resposta.text if resposta.text else "{}"

            # Higienização defensiva: remove tags de bloco markdown (```json / ```) e espaços extras
            texto_limpo = (
                texto_bruto.replace("```json", "")
                .replace("```JSON", "")
                .replace("```", "")
                .strip()
            )

            # Parsing do JSON limpo
            dados = json.loads(texto_limpo)
            titulo_curado = str(dados.get("titulo_curado", titulo_original)).strip()
            resumo = str(dados.get("resumo", "Resumo não disponível.")).strip()

            # Validação defensiva dos pontos principais (lista com 3 itens)
            pontos_raw = dados.get("pontos_principais", [])
            if isinstance(pontos_raw, list):
                pontos_principais = [
                    str(p).strip() for p in pontos_raw if str(p).strip()
                ][:3]
            elif isinstance(pontos_raw, str) and pontos_raw.strip():
                pontos_principais = [pontos_raw.strip()]
            else:
                pontos_principais = []

            impacto = str(
                dados.get("impacto", "Aguardando desdobramentos adicionais do setor.")
            ).strip()

            return {
                "titulo_original": titulo_original,
                "titulo_curado":   titulo_curado,
                "resumo":          resumo,
                "pontos_principais": pontos_principais,
                "impacto":         impacto,
                "link":            link_original,
                "imagem_url":      imagem_url,
                "nome_fonte":      nome_fonte,
            }

        except json.JSONDecodeError as json_err:
            print(
                f"[!] Erro ao decodificar JSON retornado pela IA (Tentativa {tentativa}/{max_tentativas}): {json_err}"
            )
            if tentativa < max_tentativas:
                time.sleep(2)
                continue
            return {
                "titulo_original": titulo_original,
                "titulo_curado":   titulo_original,
                "resumo":          "Falha na estrutura de dados retornada pela IA.",
                "pontos_principais": ["Processamento automático via pipeline."],
                "impacto":         "Consulte a matéria completa na íntegra.",
                "link":            link_original,
                "imagem_url":      imagem_url,
                "nome_fonte":      nome_fonte,
            }

        except Exception as e:
            erro_msg = str(e)
            print(
                f"[!] Erro na API do Gemini (Tentativa {tentativa}/{max_tentativas}): {erro_msg}"
            )

            # Tratamento de erro 503 / sobrecarga temporária
            if any(
                termo in erro_msg.upper()
                for termo in ["503", "UNAVAILABLE", "OVERLOADED", "RESOURCE_EXHAUSTED"]
            ):
                if tentativa < max_tentativas:
                    print(
                        f"[*] API temporariamente indisponível. Aguardando {intervalo_retry}s antes de tentar novamente..."
                    )
                    time.sleep(intervalo_retry)
                    continue
            elif tentativa < max_tentativas:
                print(
                    "[*] Ocorreu uma instabilidade. Tentando novamente em 3 segundos..."
                )
                time.sleep(3)
                continue

            return {
                "titulo_original": titulo_original,
                "titulo_curado":   titulo_original,
                "resumo":          "Falha temporária na geração com IA.",
                "pontos_principais": ["Instabilidade momentânea no processamento."],
                "impacto":         "Acompanhe as atualizações na fonte oficial.",
                "link":            link_original,
                "imagem_url":      imagem_url,
                "nome_fonte":      nome_fonte,
            }


def processar_fluxo_completo(
    limite_por_fonte: int = 2,
    limite_total_ia: int = 6,
    feeds: dict | None = None,
) -> list[dict[str, str]]:
    """
    Orquestra a extração multicanal da Fase 1, cruza os links coletados com o histórico
    local (Sistema Anticota), agrupa por fonte, e processa apenas notícias inéditas dentro
    do limite de segurança da cota da API Gemini.

    Args:
        limite_por_fonte (int): Máximo de notícias a coletar por fonte RSS.
        limite_total_ia (int): Teto global de chamadas à API Gemini por execução
                               (proteção de cota).
        feeds (dict | None): Subconjunto de feeds a usar. Se None, usa FEEDS_CONFIG completo.

    Returns:
        List[Dict]: Artigos curados pela IA com campos completos incluindo 'nome_fonte'.
    """
    print("\n" + "=" * 80)
    print(" FASE 2 — CURADORIA MULTICANAL COM IA (GEMINI)")
    print("=" * 80)

    # 1. Coleta unificada de todas as fontes configuradas
    print(f"\n[1/3] Coletando feeds multicanal (até {limite_por_fonte} por fonte)...")
    feeds_alvo = feeds or FEEDS_CONFIG
    noticias_brutas = coletar_todos_os_feeds(
        feeds=feeds_alvo, limite_por_fonte=limite_por_fonte
    )

    if not noticias_brutas:
        print("[!] Nenhuma notícia encontrada em nenhuma das fontes.")
        return []

    # Agrupa contagem por fonte para exibição
    fontes_contagem: dict[str, int] = {}
    for n in noticias_brutas:
        f = n.get("nome_fonte", "Desconhecida")
        fontes_contagem[f] = fontes_contagem.get(f, 0) + 1

    print(f"    Distribuição por fonte: { {k: v for k, v in fontes_contagem.items()} }")

    # 2. Sistema Anticota: filtra apenas URLs inéditas
    print("\n[2/3] Consultando cache local (Sistema Anticota)...")
    historico = carregar_historico()
    historico_set = set(historico)

    noticias_ineditas = [
        n for n in noticias_brutas
        if n.get("link") and n["link"].strip() not in historico_set
    ]

    qtd_total   = len(noticias_brutas)
    qtd_ignoradas = qtd_total - len(noticias_ineditas)
    qtd_ineditas  = len(noticias_ineditas)

    print(
        f"  -> {qtd_total} coletadas: {qtd_ignoradas} já processadas (ignoradas), "
        f"{qtd_ineditas} inédita(s) disponíveis para IA."
    )

    if not noticias_ineditas:
        print("\n" + "=" * 80)
        print("[INFO] Todas as notícias coletadas já foram processadas anteriormente.")
        print("[OK] Execução encerrada de forma limpa sem chamadas à API Gemini (Cota preservada!).")
        print("=" * 80 + "\n")
        return []

    # Ordena: prioriza fontes com menos registros no histórico (mais novidade)
    # e dentro de cada fonte mantém a ordem de chegada do feed
    fontes_no_historico: dict[str, int] = {}
    for url in historico:
        for n in noticias_brutas:
            if n.get("link", "").strip() == url:
                f = n.get("nome_fonte", "")
                fontes_no_historico[f] = fontes_no_historico.get(f, 0) + 1

    noticias_ordenadas = sorted(
        noticias_ineditas,
        key=lambda n: fontes_no_historico.get(n.get("nome_fonte", ""), 0)
    )

    # Aplica o teto global de chamadas à IA
    a_processar = noticias_ordenadas[:limite_total_ia]
    cortadas = len(noticias_ineditas) - len(a_processar)

    if cortadas > 0:
        print(
            f"  [!] Limite de cota aplicado: {limite_total_ia} de {qtd_ineditas} inéditas serão enviadas à IA "
            f"({cortadas} reservadas para próxima execução)."
        )

    # 3. Processa com a IA
    print(f"\n[3/3] Inicializando Gemini e curando {len(a_processar)} matéria(s)...\n")
    cliente = obter_cliente_gemini()

    artigos_curados: list[dict[str, Any]] = []
    urls_processadas: list[str] = []

    for i, noticia in enumerate(a_processar, start=1):
        fonte = noticia.get("nome_fonte", "?")
        print(f" -> [{fonte}] Curando [{i}/{len(a_processar)}]: {noticia['titulo'][:55]}...")
        artigo = curar_noticia_com_ia(
            cliente=cliente,
            titulo_original=noticia["titulo"],
            link_original=noticia["link"],
            nome_fonte=fonte,
            imagem_url=noticia.get("imagem_url"),
            modelo="gemini-3.6-flash",
        )
        artigos_curados.append(artigo)
        if noticia.get("link"):
            urls_processadas.append(noticia["link"].strip())

    # Grava as novas URLs no histórico local
    if urls_processadas:
        salvar_historico(urls_processadas)

    # Exibe os resultados finais no terminal
    print("\n" + "=" * 80)
    print(" PORTAL DE NOTÍCIAS - CONTEÚDO CURADO POR IA (FASE 2 - MULTICANAL)")
    print("=" * 80)

    for idx, art in enumerate(artigos_curados, start=1):
        print(f"\n[NOTÍCIA #{idx}] [{art.get('nome_fonte', '?')}]")
        print(f"📌 Original: {art['titulo_original']}")
        print(f"✨ Curado  : {art['titulo_curado']}")
        print(f"🖼️ Imagem  : {art.get('imagem_url') or '[Sem imagem oficial]'}")
        print(f"📝 Resumo  : {art['resumo']}")
        print("🎯 Destaques:")
        for ponto in art.get("pontos_principais", []):
            print(f"   • {ponto}")
        print(f"💡 Impacto : {art.get('impacto')}")
        print(f"🔗 Fonte   : {art['link']}")
        print("-" * 80)

    print(
        f"\n[OK] Fase 2 concluída! {len(artigos_curados)} artigo(s) inédito(s) gerado(s) com sucesso."
    )
    return artigos_curados


if __name__ == "__main__":
    processar_fluxo_completo(limite_por_fonte=2, limite_total_ia=6)

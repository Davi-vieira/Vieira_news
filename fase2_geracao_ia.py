"""
MÓDULO: Fase 2 - Curadoria e Geração com IA (Google Gemini API)
OBJETIVO: Processar os dados brutos minerados na Fase 1 utilizando o modelo Gemini
          com saída forçada em JSON estruturado (application/json) e higienização defensiva de strings.
          Inclui mecanismo de retry resiliente contra instabilidades (ex: 503 UNAVAILABLE).
"""
import json
import os
import sys
import time
from typing import Dict, List
from google import genai
from google.genai import types

# Garante suporte a caracteres UTF-8 no terminal do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Importa o extrator modular da Fase 1
from fase1_coleta_rss import FEEDS_CONFIG, coletar_noticias_rss


def obter_cliente_gemini() -> genai.Client:
    """
    Valida a existência da variável de ambiente GEMINI_API_KEY e instancia o cliente oficial.
    
    Returns:
        genai.Client: Instância autenticada do cliente Google GenAI.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("\n" + "!" * 80)
        print("[ERRO DE SEGURANÇA] Variável de ambiente 'GEMINI_API_KEY' não encontrada!")
        print("Para proteger sua credencial, nunca insira a chave direto no código.")
        print("Configure no PowerShell com: $env:GEMINI_API_KEY=\"sua_chave_aqui\"")
        print("!" * 80 + "\n")
        sys.exit(1)
        
    return genai.Client(api_key=api_key)


def curar_noticia_com_ia(
    cliente: genai.Client,
    titulo_original: str,
    link_original: str,
    modelo: str = "gemini-3.6-flash",
    max_tentativas: int = 3,
    intervalo_retry: int = 10
) -> Dict[str, str]:
    """
    Envia a notícia bruta para o Google Gemini gerar uma versão curada por IA utilizando
    saída em JSON estruturado com higienização de Markdown e limite expandido de tokens.
    
    Args:
        cliente (genai.Client): Cliente autenticado da API.
        titulo_original (str): Manchete original extraída do RSS.
        link_original (str): Link da matéria original.
        modelo (str): Identificador do modelo leve na API do Google (padrão: gemini-3.6-flash).
        max_tentativas (int): Quantidade máxima de tentativas em caso de instabilidade.
        intervalo_retry (int): Tempo de espera em segundos para erros temporários (503).

    Returns:
        Dict[str, str]: Dicionário contendo título curado, resumo e metadados.
    """
    system_instruction = (
        "Você é um jornalista sênior, ético e imparcial em um portal de notícias de tecnologia e atualidades.\n"
        "Sua resposta deve ser ESTRITAMENTE um objeto JSON válido contendo exatamente as chaves:\n"
        "- 'titulo_curado': um novo título profissional, claro e atrativo (sem sensacionalismo/clickbait).\n"
        "- 'resumo': um parágrafo conciso (3 a 4 frases) seguindo a estrutura de pirâmide invertida (foco em quem, o que e impacto), em tom neutro e formal.\n"
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
                    response_mime_type="application/json"
                )
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
            titulo_curado = dados.get("titulo_curado", titulo_original).strip()
            resumo = dados.get("resumo", "Resumo não disponível.").strip()

            return {
                "titulo_original": titulo_original,
                "titulo_curado": titulo_curado,
                "resumo": resumo,
                "link": link_original
            }

        except json.JSONDecodeError as json_err:
            print(f"[!] Erro ao decodificar JSON retornado pela IA (Tentativa {tentativa}/{max_tentativas}): {json_err}")
            if tentativa < max_tentativas:
                time.sleep(2)
                continue
            return {
                "titulo_original": titulo_original,
                "titulo_curado": titulo_original,
                "resumo": "Falha na estrutura de dados retornada pela IA.",
                "link": link_original
            }

        except Exception as e:
            erro_msg = str(e)
            print(f"[!] Erro na API do Gemini (Tentativa {tentativa}/{max_tentativas}): {erro_msg}")
            
            # Tratamento de erro 503 / sobrecarga temporária
            if any(termo in erro_msg.upper() for termo in ["503", "UNAVAILABLE", "OVERLOADED", "RESOURCE_EXHAUSTED"]):
                if tentativa < max_tentativas:
                    print(f"[*] API temporariamente indisponível. Aguardando {intervalo_retry}s antes de tentar novamente...")
                    time.sleep(intervalo_retry)
                    continue
            elif tentativa < max_tentativas:
                print(f"[*] Ocorreu uma instabilidade. Tentando novamente em 3 segundos...")
                time.sleep(3)
                continue
                
            return {
                "titulo_original": titulo_original,
                "titulo_curado": titulo_original,
                "resumo": "Falha temporária na geração com IA.",
                "link": link_original
            }


def processar_fluxo_completo(limite_noticias: int = 3, feed_chave: str = "g1_tecnologia") -> List[Dict[str, str]]:
    """
    Orquestra a extração da Fase 1 e a curadoria da Fase 2, retornando a lista final de notícias curadas.
    """
    print(f"\n[1/3] Inicializando cliente Gemini e validando credenciais...")
    cliente = obter_cliente_gemini()
    
    print(f"[2/3] Coletando {limite_noticias} notícias recentes do feed '{feed_chave}'...")
    url_feed = FEEDS_CONFIG.get(feed_chave, FEEDS_CONFIG["g1_tecnologia"])
    noticias_brutas = coletar_noticias_rss(url_feed=url_feed, limite=limite_noticias)
    
    if not noticias_brutas:
        print("[!] Nenhuma notícia para processar.")
        return []

    print(f"[3/3] Processando com IA (Google Gemini - JSON Estruturado 1000 Tokens)...\n")
    
    artigos_curados = []
    for i, noticia in enumerate(noticias_brutas, start=1):
        print(f" -> Curando notícia [{i}/{len(noticias_brutas)}]: {noticia['titulo'][:50]}...")
        artigo = curar_noticia_com_ia(
            cliente=cliente,
            titulo_original=noticia["titulo"],
            link_original=noticia["link"],
            modelo="gemini-3.6-flash"
        )
        artigos_curados.append(artigo)
        
    # Exibe os resultados finais estruturados no terminal
    print("\n" + "=" * 80)
    print(" PORTAL DE NOTÍCIAS - CONTEÚDO CURADO POR IA (FASE 2 - JSON)")
    print("=" * 80)
    
    for idx, art in enumerate(artigos_curados, start=1):
        print(f"\n[NOTÍCIA #{idx}]")
        print(f"📌 Original: {art['titulo_original']}")
        print(f"✨ Curado  : {art['titulo_curado']}")
        print(f"📝 Resumo  : {art['resumo']}")
        print(f"🔗 Fonte   : {art['link']}")
        print("-" * 80)

    print(f"\n[OK] Fase 2 concluída! {len(artigos_curados)} artigos gerados com sucesso.")
    return artigos_curados


if __name__ == "__main__":
    processar_fluxo_completo(limite_noticias=3, feed_chave="g1_tecnologia")

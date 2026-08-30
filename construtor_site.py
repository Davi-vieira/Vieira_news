"""
MÓDULO: Fase 4 - Frontend Builder (Construtor do Site Estático)
OBJETIVO: Varrer os arquivos Markdown gerados na Fase 3 dentro da pasta 'noticias_prontas',
          converter o conteúdo para HTML com formatação moderna e injetar em um template
          responsivo, moderno e elegante utilizando Tailwind CSS.
          O resultado final é compilado e salvo em 'public/index.html'.
"""

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Garante suporte a caracteres UTF-8 no terminal do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Tentativa de importação da biblioteca markdown com fallback seguro
try:
    import markdown
except ImportError:
    print("\n" + "!" * 80)
    print("[ERRO] A biblioteca 'markdown' não está instalada no ambiente Python atual.")
    print("Execute no terminal:")
    print("    pip install markdown")
    print("!" * 80 + "\n")
    sys.exit(1)


MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def formatar_data_pt(dt: datetime) -> str:
    """Formata data no padrão brasileiro de forma independente do locale do SO."""
    mes = MESES_PT.get(dt.month, "")
    return f"{dt.day:02d} de {mes} de {dt.year} às {dt.strftime('%H:%M')}"


def formatar_data_curta_pt(dt: datetime) -> str:
    """Formata data no padrão dd/mm/aaaa hh:mm."""
    return dt.strftime("%d/%m/%Y às %H:%M")


def extrair_categoria_automatica(titulo: str, conteudo: str) -> str:
    """
    Identifica uma categoria editorial com base em palavras-chave no título e no conteúdo.
    """
    texto_combinado = f"{titulo} {conteudo}".lower()

    regras = [
        (
            "Inteligência Artificial",
            [
                "ia",
                "inteligência artificial",
                "chatgpt",
                "gemini",
                "llm",
                "openai",
                "machine learning",
            ],
        ),
        (
            "Segurança Digital",
            [
                "segurança",
                "hacker",
                "golpe",
                "vazamento",
                "privacidade",
                "lei",
                "regulação",
                "restrição",
                "crianças",
            ],
        ),
        (
            "Carreira & Negócios",
            [
                "banco",
                "salário",
                "vaga",
                "mercado",
                "profissionais",
                "investimento",
                "bilhões",
                "startup",
                "carreira",
            ],
        ),
        (
            "Dispositivos & Apps",
            [
                "smartphone",
                "apple",
                "google",
                "android",
                "ios",
                "aplicativo",
                "celular",
                "computador",
            ],
        ),
        (
            "Inovação & Ciência",
            ["ciência", "pesquisa", "estudo", "espacial", "robô", "energia", "futuro"],
        ),
    ]

    for categoria, palavras in regras:
        for p in palavras:
            if re.search(rf"\b{re.escape(p)}\b", texto_combinado):
                return categoria

    return "Tecnologia"


def calcular_tempo_leitura(texto: str) -> str:
    """Calcula o tempo estimado de leitura em minutos."""
    palavras = len(re.findall(r"\w+", texto))
    minutos = max(1, round(palavras / 180))
    return f"{minutos} min de leitura"


def processar_arquivo_markdown(caminho_arquivo: Path) -> dict[str, Any] | None:
    """
    Lê um arquivo .md, extrai metadados (Título, Imagem, Resumo, Fonte) e converte para HTML.

    Args:
        caminho_arquivo (Path): Caminho para o arquivo .md.

    Returns:
        Optional[Dict[str, Any]]: Dicionário com os dados processados da notícia.
    """
    try:
        conteudo_bruto = caminho_arquivo.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  [!] Erro ao ler '{caminho_arquivo.name}': {e}")
        return None

    # 1. Extração do Título (# Título)
    match_titulo = re.search(r"^#\s+(.+)$", conteudo_bruto, re.MULTILINE)
    titulo = (
        match_titulo.group(1).strip()
        if match_titulo
        else caminho_arquivo.stem.replace("-", " ").title()
    )

    # 2. Extração da Imagem (![alt](url))
    match_imagem = re.search(r"!\[.*?\]\((https?://[^\s\)]+)\)", conteudo_bruto)
    imagem_url = (
        match_imagem.group(1)
        if match_imagem
        else f"https://picsum.photos/seed/{caminho_arquivo.stem}/800/450"
    )

    # 3. Extração da Fonte Original (link markdown [texto](url))
    match_fonte = re.search(r"\[(.*?)\]\((https?://[^\s\)]+)\)", conteudo_bruto)
    if match_fonte:
        fonte_nome = match_fonte.group(1).strip()
        fonte_url = match_fonte.group(2).strip()
    else:
        fonte_nome = "Portal de Notícias Original"
        fonte_url = "#"

    # 4. Extração do Resumo / Corpo textual da notícia
    conteudo_sem_header = re.sub(r"^#\s+.+$", "", conteudo_bruto, flags=re.MULTILINE)
    conteudo_sem_header = re.sub(r"!\[.*?\]\(.*?\)", "", conteudo_sem_header)
    conteudo_sem_header = re.sub(
        r"🔗\s*\*\*Fonte Original:\*\*.*$", "", conteudo_sem_header, flags=re.MULTILINE
    )
    conteudo_sem_header = re.sub(
        r"\*Publicado automaticamente.*$", "", conteudo_sem_header, flags=re.MULTILINE
    )
    conteudo_sem_header = re.sub(
        r"^##\s+Resumo da Notícia", "", conteudo_sem_header, flags=re.MULTILINE
    )
    conteudo_sem_header = re.sub(
        r"^---\s*$", "", conteudo_sem_header, flags=re.MULTILINE
    )

    texto_resumo_puro = conteudo_sem_header.strip()

    # Se a IA retornou erro ou vazio, coloca mensagem amigável
    if not texto_resumo_puro or "Falha na estrutura" in texto_resumo_puro:
        texto_resumo_puro = "Esta notícia foi coletada e curada pelo pipeline automatizado. Clique no botão de fonte para acessar o artigo completo na íntegra."

    # 5. Conversão Markdown completa para HTML
    html_completo = markdown.markdown(
        conteudo_bruto, extensions=["extra", "nl2br", "sane_lists", "toc"]
    )

    # 6. Data de modificação do arquivo ou data atual
    try:
        timestamp_mod = caminho_arquivo.stat().st_mtime
        dt_mod = datetime.fromtimestamp(timestamp_mod)
        data_formatada = formatar_data_curta_pt(dt_mod)
        data_iso = dt_mod.isoformat()
    except Exception:
        dt_mod = datetime.now()
        data_formatada = formatar_data_curta_pt(dt_mod)
        data_iso = dt_mod.isoformat()

    categoria = extrair_categoria_automatica(titulo, texto_resumo_puro)
    tempo_leitura = calcular_tempo_leitura(texto_resumo_puro)

    return {
        "slug": caminho_arquivo.stem,
        "arquivo": caminho_arquivo.name,
        "titulo": titulo,
        "imagem_url": imagem_url,
        "resumo_texto": texto_resumo_puro,
        "resumo_curto": (texto_resumo_puro[:160] + "...")
        if len(texto_resumo_puro) > 160
        else texto_resumo_puro,
        "html_completo": html_completo,
        "fonte_nome": fonte_nome,
        "fonte_url": fonte_url,
        "categoria": categoria,
        "tempo_leitura": tempo_leitura,
        "data_formatada": data_formatada,
        "data_iso": data_iso,
        "timestamp": caminho_arquivo.stat().st_mtime if caminho_arquivo.exists() else 0,
    }


def ler_todas_noticias(pasta_origem: str = "noticias_prontas") -> list[dict[str, Any]]:
    """
    Varre a pasta de notícias prontas, processa todos os arquivos .md e retorna ordenados.

    Args:
        pasta_origem (str): Nome da pasta contendo os arquivos .md.

    Returns:
        List[Dict[str, Any]]: Lista de notícias prontas para exibição.
    """
    diretorio = Path.cwd() / pasta_origem

    if not diretorio.exists():
        print(
            f"[AVISO] A pasta '{pasta_origem}' não existe. Criando diretório vazio..."
        )
        diretorio.mkdir(parents=True, exist_ok=True)
        return []

    arquivos_md = list(diretorio.glob("*.md"))
    print(
        f"[+] Encontrados {len(arquivos_md)} arquivo(s) .md em '{diretorio.resolve()}'."
    )

    noticias = []
    for arq in arquivos_md:
        dados = processar_arquivo_markdown(arq)
        if dados:
            noticias.append(dados)

    # Ordena por timestamp mais recente primeiro
    noticias.sort(key=lambda x: x["timestamp"], reverse=True)
    return noticias


def gerar_template_html(noticias: list[dict[str, Any]]) -> str:
    """
    Gera o código HTML completo e autônomo com Tailwind CSS, layout de portal de notícias,
    seção de destaque, grid responsivo, pesquisa em tempo real e leitor modal.
    """
    agora_formatado = formatar_data_pt(datetime.now())
    ano_atual = datetime.now().year
    qtd_noticias = len(noticias)

    # Serializa notícias para uso seguro no JavaScript do frontend (busca e modal)
    noticias_json_safe = json.dumps(
        [
            {
                "slug": n["slug"],
                "titulo": n["titulo"],
                "imagem_url": n["imagem_url"],
                "resumo_texto": n["resumo_texto"],
                "categoria": n["categoria"],
                "tempo_leitura": n["tempo_leitura"],
                "data_formatada": n["data_formatada"],
                "fonte_url": n["fonte_url"],
                "fonte_nome": n["fonte_nome"],
                "html_completo": n["html_completo"],
            }
            for n in noticias
        ],
        ensure_ascii=False,
    )

    # Identifica a notícia de destaque (primeira notícia mais recente)
    destaque = noticias[0] if noticias else None
    demais_noticias = noticias[1:] if len(noticias) > 1 else []

    # Bloco HTML para Notícia de Destaque (Hero Section)
    if destaque:
        html_destaque = f"""
        <div class="relative overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl transition-all duration-300 hover:border-indigo-500/50 group mb-12">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-0">
                <div class="lg:col-span-7 relative h-72 sm:h-96 lg:h-auto overflow-hidden bg-slate-950">
                    <img src="{destaque["imagem_url"]}" alt="{html.escape(destaque["titulo"])}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 opacity-90 group-hover:opacity-100" onerror="this.src='https://picsum.photos/800/450?grayscale'" />
                    <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-slate-900"></div>
                    <div class="absolute top-4 left-4 flex items-center space-x-2">
                        <span class="px-3 py-1 text-xs font-bold uppercase tracking-wider bg-rose-600/90 text-white rounded-full backdrop-blur-md shadow-lg flex items-center gap-1.5">
                            <span class="w-2 h-2 rounded-full bg-white animate-ping"></span>
                            Destaque Principal
                        </span>
                        <span class="px-3 py-1 text-xs font-semibold bg-slate-900/80 text-cyan-300 rounded-full border border-cyan-500/30 backdrop-blur-md">
                            {destaque["categoria"]}
                        </span>
                    </div>
                </div>
                <div class="lg:col-span-5 p-6 sm:p-8 lg:p-10 flex flex-col justify-between bg-slate-900/95">
                    <div>
                        <div class="flex items-center text-xs text-slate-400 space-x-3 mb-3">
                            <span>📅 {destaque["data_formatada"]}</span>
                            <span>•</span>
                            <span>⏱️ {destaque["tempo_leitura"]}</span>
                        </div>
                        <h2 class="text-2xl sm:text-3xl font-extrabold text-white leading-tight mb-4 tracking-tight group-hover:text-indigo-300 transition-colors">
                            {destaque["titulo"]}
                        </h2>
                        <p class="text-slate-300 text-sm sm:text-base leading-relaxed mb-6 line-clamp-4">
                            {destaque["resumo_texto"]}
                        </p>
                    </div>
                    <div class="flex flex-wrap items-center gap-3 pt-4 border-t border-slate-800">
                        <button onclick="abrirModal('{destaque["slug"]}')" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 hover:shadow-indigo-500/50 transition-all flex items-center gap-2 cursor-pointer">
                            <span>Ler Notícia Completa</span>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                        </button>
                        <a href="{destaque["fonte_url"]}" target="_blank" rel="noopener noreferrer" class="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-sm border border-slate-700 transition-all flex items-center gap-2">
                            <span>Fonte Original</span>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        </a>
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        html_destaque = """
        <div class="rounded-3xl bg-slate-900/60 border border-slate-800 p-12 text-center my-8">
            <div class="w-16 h-16 bg-indigo-500/10 text-indigo-400 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path></svg>
            </div>
            <h3 class="text-xl font-bold text-white mb-2">Nenhuma notícia encontrada</h3>
            <p class="text-slate-400 max-w-md mx-auto text-sm">Execute a Fase 3 para coletar e gerar novos arquivos .md na pasta <code>noticias_prontas</code>.</p>
        </div>
        """

    # Bloco HTML para os Cards de Notícias no Grid
    cards_html = ""
    for noticia in demais_noticias if destaque else []:
        cards_html += f"""
        <article class="noticia-card flex flex-col bg-slate-900 border border-slate-800/80 rounded-2xl overflow-hidden hover:border-indigo-500/40 hover:shadow-xl hover:shadow-indigo-500/5 transition-all duration-300 group" data-categoria="{noticia["categoria"]}" data-titulo="{html.escape(noticia["titulo"].lower())}">
            <div class="relative h-48 overflow-hidden bg-slate-950">
                <img src="{noticia["imagem_url"]}" alt="{html.escape(noticia["titulo"])}" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 opacity-90 group-hover:opacity-100" loading="lazy" onerror="this.src='https://picsum.photos/400/250?grayscale'" />
                <div class="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/20 to-transparent"></div>
                <div class="absolute top-3 left-3">
                    <span class="px-2.5 py-0.5 text-xs font-semibold bg-slate-900/90 text-cyan-300 rounded-full border border-cyan-500/30 backdrop-blur-md">
                        {noticia["categoria"]}
                    </span>
                </div>
                <div class="absolute bottom-3 right-3 text-[11px] font-medium text-slate-300 bg-slate-950/80 px-2 py-0.5 rounded backdrop-blur-sm">
                    ⏱️ {noticia["tempo_leitura"]}
                </div>
            </div>
            <div class="p-5 flex-1 flex flex-col justify-between">
                <div>
                    <div class="text-xs text-slate-400 mb-2 flex items-center gap-2">
                        <span>📅 {noticia["data_formatada"]}</span>
                    </div>
                    <h3 class="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors leading-snug mb-3 line-clamp-2">
                        {noticia["titulo"]}
                    </h3>
                    <p class="text-slate-400 text-sm leading-relaxed mb-4 line-clamp-3">
                        {noticia["resumo_texto"]}
                    </p>
                </div>
                <div class="pt-4 border-t border-slate-800/80 flex items-center justify-between gap-2 mt-auto">
                    <button onclick="abrirModal('{noticia["slug"]}')" class="text-indigo-400 hover:text-indigo-300 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer">
                        <span>Ler síntese</span>
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                    </button>
                    <a href="{noticia["fonte_url"]}" target="_blank" rel="noopener noreferrer" class="text-slate-400 hover:text-white text-xs font-medium bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1">
                        <span>Fonte</span>
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                </div>
            </div>
        </article>
        """

    # Template HTML Raiz
    html_final = f"""<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vieira News | Portal de Notícias Inteligente</title>
    <meta name="description" content="Portal de notícias com curadoria automatizada via Inteligência Artificial (Google Gemini) e geração estática ultrarrápida.">
    
    <!-- Google Fonts: Inter & Plus Jakarta Sans -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
                    }},
                    colors: {{
                        brand: {{
                            50: '#eef2ff',
                            100: '#e0e7ff',
                            400: '#818cf8',
                            500: '#6366f1',
                            600: '#4f46e5',
                            700: '#4338ca',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            background-color: #030712;
            color: #f3f4f6;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        .prose-custom h1 {{ font-size: 1.75rem; font-weight: 800; color: #ffffff; margin-bottom: 1rem; }}
        .prose-custom h2 {{ font-size: 1.25rem; font-weight: 700; color: #818cf8; margin-top: 1.5rem; margin-bottom: 0.75rem; }}
        .prose-custom p {{ color: #cbd5e1; line-height: 1.8; margin-bottom: 1rem; }}
        .prose-custom img {{ border-radius: 1rem; margin: 1.5rem 0; width: 100%; border: 1px solid #1e293b; }}
        .prose-custom hr {{ border-color: #1e293b; margin: 1.5rem 0; }}
        .prose-custom a {{ color: #38bdf8; text-decoration: underline; }}
        .prose-custom strong {{ color: #ffffff; }}
        /* Custom Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #030712; }}
        ::-webkit-scrollbar-thumb {{ background: #1f2937; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #374151; }}
    </style>
</head>
<body class="min-h-screen flex flex-col selection:bg-indigo-500 selection:text-white bg-[#030712]">

    <!-- Barra de Notificação Superior / Status do Bot -->
    <div class="bg-gradient-to-r from-indigo-950 via-slate-900 to-indigo-950 border-b border-indigo-900/40 text-xs py-2 px-4">
        <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center space-x-2">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
                    PIPELINE ATIVO
                </span>
                <span class="text-slate-400">Curadoria automatizada com <strong class="text-indigo-300">Google Gemini IA</strong> &amp; <strong class="text-indigo-300">Python 3.12</strong></span>
            </div>
            <div class="flex items-center space-x-4 text-slate-400">
                <span>🕒 Atualizado em: <span class="text-slate-200">{agora_formatado}</span></span>
                <span class="hidden sm:inline">•</span>
                <span class="hidden sm:inline">📊 <strong>{qtd_noticias}</strong> artigos publicados</span>
            </div>
        </div>
    </div>

    <!-- Header Principal / Navbar -->
    <header class="sticky top-0 z-40 bg-[#030712]/90 backdrop-blur-xl border-b border-slate-800/80">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30 font-black text-xl text-white">
                    V
                </div>
                <div>
                    <a href="#" class="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                        VIEIRA<span class="text-indigo-400 font-extrabold">NEWS</span>
                        <span class="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30">AI Portal</span>
                    </a>
                    <p class="text-[11px] text-slate-400">Portal de Notícias em Tempo Real &amp; Curadoria com IA</p>
                </div>
            </div>

            <!-- Campo de Busca e Filtro Rápido -->
            <div class="w-full md:w-auto flex-1 max-w-md">
                <div class="relative">
                    <input type="text" id="campoBusca" placeholder="Pesquisar notícias por palavras-chave..." 
                           class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 pl-10 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all">
                    <svg class="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                    </svg>
                </div>
            </div>

            <!-- Botões de Ação do Header -->
            <div class="flex items-center space-x-3">
                <a href="https://github.com/Davi-vieira/Vieira_news" target="_blank" rel="noopener noreferrer" class="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 text-xs font-semibold transition-all flex items-center gap-2">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>
                    <span>Repositório</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Barra de Filtros de Categorias -->
    <div class="border-b border-slate-900 bg-slate-950/60 py-3">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center space-x-2 overflow-x-auto no-scrollbar">
            <span class="text-xs text-slate-500 font-semibold uppercase tracking-wider mr-2 shrink-0">Categorias:</span>
            <button onclick="filtrarCategoria('todas')" class="btn-filtro active px-3.5 py-1 rounded-full text-xs font-semibold bg-indigo-600 text-white transition-all shrink-0">
                Todas ({qtd_noticias})
            </button>
            <button onclick="filtrarCategoria('Inteligência Artificial')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">
                🤖 Inteligência Artificial
            </button>
            <button onclick="filtrarCategoria('Segurança Digital')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">
                🔒 Segurança Digital
            </button>
            <button onclick="filtrarCategoria('Carreira & Negócios')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">
                💼 Carreira & Negócios
            </button>
            <button onclick="filtrarCategoria('Tecnologia')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">
                ⚡ Tecnologia Geral
            </button>
        </div>
    </div>

    <!-- Conteúdo Principal -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        <!-- Notícia Destaque Principal -->
        <div id="secaoDestaque">
            {html_destaque}
        </div>

        <!-- Título da Seção de Notícias do Grid -->
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center space-x-2">
                <div class="w-2.5 h-6 bg-indigo-500 rounded-full"></div>
                <h3 class="text-xl font-extrabold text-white tracking-tight">Últimas Notícias Curadas</h3>
            </div>
            <span class="text-xs text-slate-400 font-medium" id="contadorResultados">Exibindo todas as matérias</span>
        </div>

        <!-- Grid de Cards de Notícias -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="gridNoticias">
            {cards_html if cards_html else '<p class="col-span-full text-center text-slate-500 py-6">Nenhuma notícia secundária no momento.</p>'}
        </div>

        <!-- Mensagem de Nenhum Resultado da Busca -->
        <div id="semResultados" class="hidden text-center py-16 bg-slate-900/30 rounded-3xl border border-slate-800/80 my-8">
            <div class="w-12 h-12 bg-slate-800 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            </div>
            <h4 class="text-lg font-bold text-white mb-1">Nenhuma notícia encontrada</h4>
            <p class="text-sm text-slate-400">Tente buscar por outro termo ou limpar os filtros de categoria.</p>
        </div>

    </main>

    <!-- Modal de Leitura Completa da Notícia -->
    <div id="modalNoticia" class="fixed inset-0 z-50 hidden overflow-y-auto bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 transition-all duration-300">
        <div class="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            <!-- Header do Modal -->
            <div class="p-6 border-b border-slate-800 flex items-start justify-between bg-slate-900/90 sticky top-0 z-10">
                <div class="pr-4">
                    <span id="modalCategoria" class="px-2.5 py-0.5 text-xs font-semibold bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30"></span>
                    <h3 id="modalTitulo" class="text-xl sm:text-2xl font-bold text-white mt-2 leading-tight"></h3>
                    <p class="text-xs text-slate-400 mt-1" id="modalData"></p>
                </div>
                <button onclick="fecharModal()" class="text-slate-400 hover:text-white p-2 rounded-xl bg-slate-800 hover:bg-slate-700 transition-colors cursor-pointer shrink-0">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <!-- Corpo do Modal -->
            <div class="p-6 sm:p-8 overflow-y-auto flex-1 prose-custom" id="modalCorpo">
                <!-- Conteúdo HTML do Markdown é inserido aqui -->
            </div>
            <!-- Footer do Modal -->
            <div class="p-4 sm:p-6 border-t border-slate-800 bg-slate-950 flex flex-wrap items-center justify-between gap-3">
                <span class="text-xs text-slate-500">Curado via Gemini IA</span>
                <div class="flex items-center space-x-3">
                    <button onclick="fecharModal()" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors">
                        Fechar
                    </button>
                    <a id="modalLinkOriginal" href="#" target="_blank" rel="noopener noreferrer" class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-1.5">
                        <span>Acessar Matéria Completa no Portal Oficial</span>
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer Moderno -->
    <footer class="border-t border-slate-800 bg-slate-950 text-slate-400 py-12 mt-16">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
                <div class="md:col-span-2">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 flex items-center justify-center font-black text-sm text-white">
                            V
                        </div>
                        <span class="text-xl font-bold text-white">Vieira News</span>
                    </div>
                    <p class="text-sm text-slate-400 leading-relaxed max-w-sm mb-4">
                        Portal moderno de notícias com pipeline 100% automatizado: coleta RSS, sintetização e curadoria com Inteligência Artificial e publicação estática contínua via GitHub Actions.
                    </p>
                    <div class="flex flex-wrap gap-2">
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">Python 3.12</span>
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">Google Gemini IA</span>
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">Tailwind CSS</span>
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">GitHub Actions</span>
                    </div>
                </div>
                <div>
                    <h5 class="text-xs font-bold uppercase tracking-wider text-slate-200 mb-4">Etapas do Pipeline</h5>
                    <ul class="space-y-2 text-xs text-slate-400">
                        <li><span class="text-indigo-400 font-semibold">Fase 1:</span> Coleta de RSS Feeds</li>
                        <li><span class="text-indigo-400 font-semibold">Fase 2:</span> Curadoria com Gemini IA</li>
                        <li><span class="text-indigo-400 font-semibold">Fase 3:</span> Geração Markdown (CMS)</li>
                        <li><span class="text-indigo-400 font-semibold">Fase 4:</span> Frontend Static Builder</li>
                    </ul>
                </div>
                <div>
                    <h5 class="text-xs font-bold uppercase tracking-wider text-slate-200 mb-4">Links &amp; Créditos</h5>
                    <ul class="space-y-2 text-xs text-slate-400">
                        <li><a href="https://github.com/Davi-vieira/Vieira_news" target="_blank" class="hover:text-white transition-colors">Repositório no GitHub ↗</a></li>
                        <li><a href="https://g1.globo.com/tecnologia/" target="_blank" class="hover:text-white transition-colors">G1 Tecnologia (Fonte RSS) ↗</a></li>
                        <li><a href="https://ai.google.dev/" target="_blank" class="hover:text-white transition-colors">Google AI Studio ↗</a></li>
                    </ul>
                </div>
            </div>
            <div class="pt-8 border-t border-slate-900 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
                <p>&copy; {ano_atual} Vieira News. Desenvolvido para projetos acadêmicos e demonstração técnica.</p>
                <p>Construído com automação e Inteligência Artificial Generativa.</p>
            </div>
        </div>
    </footer>

    <!-- Dados Embutidos & Script de Interatividade -->
    <script>
        const TODAS_NOTICIAS = {noticias_json_safe};

        function abrirModal(slug) {{
            const noticia = TODAS_NOTICIAS.find(n => n.slug === slug);
            if (!noticia) return;

            document.getElementById('modalCategoria').innerText = noticia.categoria;
            document.getElementById('modalTitulo').innerText = noticia.titulo;
            document.getElementById('modalData').innerText = `Publicado em ${{noticia.data_formatada}} • ${{noticia.tempo_leitura}}`;
            document.getElementById('modalCorpo').innerHTML = noticia.html_completo;
            document.getElementById('modalLinkOriginal').href = noticia.fonte_url;
            
            const modal = document.getElementById('modalNoticia');
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }}

        function fecharModal() {{
            const modal = document.getElementById('modalNoticia');
            modal.classList.add('hidden');
            document.body.style.overflow = 'auto';
        }}

        // Fecha modal ao clicar fora do conteúdo
        document.getElementById('modalNoticia').addEventListener('click', function(e) {{
            if (e.target === this) {{
                fecharModal();
            }}
        }});

        // Fecha modal no ESC
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') fecharModal();
        }});

        // Filtragem por Busca e Categorias
        const campoBusca = document.getElementById('campoBusca');
        let categoriaAtiva = 'todas';

        function filtrarCategoria(cat) {{
            categoriaAtiva = cat;
            document.querySelectorAll('.btn-filtro').forEach(btn => {{
                if (btn.innerText.includes(cat) || (cat === 'todas' && btn.innerText.includes('Todas'))) {{
                    btn.className = 'btn-filtro active px-3.5 py-1 rounded-full text-xs font-semibold bg-indigo-600 text-white transition-all shrink-0';
                }} else {{
                    btn.className = 'btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0';
                }}
            }});
            aplicarFiltros();
        }}

        function aplicarFiltros() {{
            const termo = campoBusca.value.toLowerCase().trim();
            const cards = document.querySelectorAll('.noticia-card');
            let visiveis = 0;

            cards.forEach(card => {{
                const catCard = card.getAttribute('data-categoria');
                const titCard = card.getAttribute('data-titulo') || '';
                
                const bateCategoria = (categoriaAtiva === 'todas' || catCard === categoriaAtiva);
                const bateBusca = !termo || titCard.includes(termo);

                if (bateCategoria && bateBusca) {{
                    card.style.display = 'flex';
                    visiveis++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            const semResultados = document.getElementById('semResultados');
            const contador = document.getElementById('contadorResultados');

            if (visiveis === 0 && cards.length > 0) {{
                semResultados.classList.remove('hidden');
            }} else {{
                semResultados.classList.add('hidden');
            }}

            contador.innerText = `Exibindo ${{visiveis}} matéria(s)`;
        }}

        campoBusca.addEventListener('input', aplicarFiltros);
    </script>
</body>
</html>
"""
    return html_final


def construir_site(
    pasta_origem: str = "noticias_prontas", pasta_destino: str = "public"
) -> Path:
    """
    Executa a leitura das notícias em Markdown, compila o HTML e salva em public/index.html.

    Args:
        pasta_origem (str): Diretório dos arquivos .md.
        pasta_destino (str): Diretório de saída do site estático.

    Returns:
        Path: Caminho do arquivo index.html gerado.
    """
    print("\n" + "=" * 80)
    print(" INICIANDO FASE 4: CONSTRUTOR DO SITE ESTÁTICO (FRONTEND)")
    print("=" * 80)

    # 1. Cria a pasta public se não existir
    caminho_public = Path.cwd() / pasta_destino
    caminho_public.mkdir(parents=True, exist_ok=True)

    # 2. Lê e processa todos os arquivos .md
    noticias = ler_todas_noticias(pasta_origem)

    # 3. Gera o HTML completo
    print(
        f"\n[+] Renderizando template HTML moderno (Tailwind CSS) com {len(noticias)} notícia(s)..."
    )
    html_gerado = gerar_template_html(noticias)

    # 4. Salva em public/index.html
    arquivo_index = caminho_public / "index.html"
    try:
        arquivo_index.write_text(html_gerado, encoding="utf-8")
        tamanho_kb = len(html_gerado.encode("utf-8")) / 1024
        print(f"[✓] Site construído com sucesso: {arquivo_index.resolve()}")
        print(f"    Tamanho: {tamanho_kb:.2f} KB | Total de notícias: {len(noticias)}")
    except Exception as e:
        print(f"[!] Erro crítico ao salvar '{arquivo_index.resolve()}': {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("[OK] Fase 4 concluída com sucesso!")
    print("     Para testar localmente:")
    print(f"       Opção 1: Abra diretamente o arquivo: {arquivo_index.resolve()}")
    print("       Opção 2: Execute: python -m http.server 8000 --directory public")
    print("=" * 80 + "\n")

    return arquivo_index


if __name__ == "__main__":
    construir_site()

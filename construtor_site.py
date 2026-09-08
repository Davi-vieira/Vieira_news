"""
MÓDULO: Fase 4 - Frontend Builder (Construtor do Site Estático com Paginação)
OBJETIVO: Conectar-se ao banco de dados relacional SQLite 'portal.db', extrair as matérias
          via SQL (SELECT * FROM noticias ORDER BY data_criacao DESC), dividir em páginas
          estáticas e gerar múltiplos arquivos HTML na pasta 'public/':
          - Página 1: index.html  (Hero section + grid)
          - Demais:   pagina_2.html, pagina_3.html, etc. (apenas grid)
          Cada página inclui componente de navegação com links para anterior/próxima.
"""

import html
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Garante suporte a caracteres UTF-8 no terminal do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Importa o módulo de banco de dados relacional SQLite
from banco_dados import contar_noticias, inicializar_banco, listar_noticias

# ─── Configuração de Paginação ─────────────────────────────────────────────────
NOTICIAS_POR_PAGINA: int = 12  # Itens no grid por página (hero não conta)
# ───────────────────────────────────────────────────────────────────────────────

MESES_PT = {
    1: "Janeiro",  2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",     6: "Junho",     7: "Julho",     8: "Agosto",
    9: "Setembro", 10: "Outubro",  11: "Novembro", 12: "Dezembro",
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
    Identifica uma categoria editorial com base em palavras-chave no título e conteúdo.
    """
    texto_combinado = f"{titulo} {conteudo}".lower()

    regras = [
        ("Inteligência Artificial",
         ["ia", "inteligência artificial", "chatgpt", "gemini", "llm", "openai", "machine learning"]),
        ("Segurança Digital",
         ["segurança", "hacker", "golpe", "vazamento", "privacidade", "lei", "regulação", "restrição", "crianças"]),
        ("Carreira & Negócios",
         ["banco", "salário", "vaga", "mercado", "profissionais", "investimento", "bilhões", "startup", "carreira"]),
        ("Dispositivos & Apps",
         ["smartphone", "apple", "google", "android", "ios", "aplicativo", "celular", "computador"]),
        ("Inovação & Ciência",
         ["ciência", "pesquisa", "estudo", "espacial", "robô", "energia", "futuro"]),
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


def nome_arquivo_pagina(numero: int) -> str:
    """Retorna o nome correto do arquivo para cada número de página."""
    return "index.html" if numero == 1 else f"pagina_{numero}.html"


def carregar_noticias_do_banco(db_path: str = "portal.db") -> List[Dict[str, Any]]:
    """
    Extrai todas as notícias salvas no banco de dados SQLite (portal.db) via SQL
    (SELECT * FROM noticias ORDER BY data_criacao DESC).
    Converte a string JSON de 'pontos_principais' para lista e monta o HTML do modal.

    Returns:
        List[Dict[str, Any]]: Lista completa de notícias formatadas.
    """
    inicializar_banco(db_path)
    registros = listar_noticias(db_path=db_path)
    print(f"[+] Carregadas {len(registros)} notícia(s) diretamente do banco SQLite '{db_path}'.")

    noticias_formatadas = []
    for item in registros:
        titulo = item.get("titulo", "Sem Título")
        resumo = item.get("resumo", "Sem resumo disponível.")
        pontos = item.get("pontos_principais", [])

        if isinstance(pontos, str):
            try:
                pontos = json.loads(pontos)
            except Exception:
                pontos = [pontos]
        elif not isinstance(pontos, list):
            pontos = []

        impacto       = item.get("impacto", "")
        slug          = item.get("slug") or "noticia"
        imagem_url    = item.get("imagem_url") or f"https://picsum.photos/seed/{slug}/800/450"
        link_original = item.get("link_original") or "#"
        categoria     = item.get("categoria") or extrair_categoria_automatica(titulo, resumo)
        data_criacao_iso = item.get("data_criacao")

        try:
            dt = datetime.fromisoformat(data_criacao_iso)
            data_formatada = formatar_data_curta_pt(dt)
        except Exception:
            data_formatada = formatar_data_curta_pt(datetime.now())

        tempo_leitura = calcular_tempo_leitura(f"{resumo} {' '.join(pontos)} {impacto}")

        bullets_html = "\n".join(
            f"<li class='text-slate-300 leading-relaxed'>{html.escape(p)}</li>"
            for p in pontos if p
        )

        html_modal = f"""
        <div class="space-y-6">
            <div>
                <h4 class="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-2">Resumo da Matéria</h4>
                <p class="text-slate-200 leading-relaxed text-base">{html.escape(resumo)}</p>
            </div>
            {f'''
            <div class="bg-slate-950/70 border border-slate-800/90 rounded-2xl p-5 shadow-inner">
                <h4 class="text-xs font-bold uppercase tracking-wider text-cyan-400 mb-3 flex items-center gap-2">
                    <span>🎯</span> Pontos Principais
                </h4>
                <ul class="space-y-2 list-disc list-inside text-sm">
                    {bullets_html}
                </ul>
            </div>
            ''' if bullets_html else ''}
            {f'''
            <div class="bg-indigo-950/30 border border-indigo-900/50 rounded-2xl p-5 shadow-inner">
                <h4 class="text-xs font-bold uppercase tracking-wider text-indigo-300 mb-2 flex items-center gap-2">
                    <span>💡</span> Impacto &amp; Conclusão
                </h4>
                <p class="text-slate-300 leading-relaxed text-sm">{html.escape(impacto)}</p>
            </div>
            ''' if impacto else ''}
        </div>
        """

        noticias_formatadas.append({
            "id":              item.get("id"),
            "slug":            slug,
            "titulo":          titulo,
            "resumo_texto":    resumo,
            "resumo_curto":    (resumo[:160] + "...") if len(resumo) > 160 else resumo,
            "pontos_principais": pontos,
            "impacto":         impacto,
            "imagem_url":      imagem_url,
            "fonte_nome":      item.get("nome_fonte") or "Portal Oficial",
            "fonte_url":       link_original,
            "categoria":       categoria,
            "data_formatada":  data_formatada,
            "data_iso":        data_criacao_iso or datetime.now().isoformat(),
            "tempo_leitura":   tempo_leitura,
            "html_completo":   html_modal,
        })

    return noticias_formatadas


# ─── Blocos HTML reutilizáveis ─────────────────────────────────────────────────

def _html_cabecalho(titulo_pagina: str, agora_formatado: str, qtd_total: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo_pagina}</title>
    <meta name="description" content="Portal de notícias com curadoria automatizada via Inteligência Artificial (Google Gemini) e geração estática ultrarrápida.">

    <!-- Google Fonts -->
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
                    fontFamily: {{ sans: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'] }},
                    colors: {{
                        brand: {{
                            50: '#eef2ff', 100: '#e0e7ff', 400: '#818cf8',
                            500: '#6366f1', 600: '#4f46e5', 700: '#4338ca',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ background-color: #030712; color: #f3f4f6; font-family: 'Plus Jakarta Sans', sans-serif; }}
        .prose-custom h1 {{ font-size: 1.75rem; font-weight: 800; color: #ffffff; margin-bottom: 1rem; }}
        .prose-custom h2 {{ font-size: 1.25rem; font-weight: 700; color: #818cf8; margin-top: 1.5rem; margin-bottom: 0.75rem; }}
        .prose-custom p {{ color: #cbd5e1; line-height: 1.8; margin-bottom: 1rem; }}
        .prose-custom img {{ border-radius: 1rem; margin: 1.5rem 0; width: 100%; border: 1px solid #1e293b; }}
        .prose-custom hr {{ border-color: #1e293b; margin: 1.5rem 0; }}
        .prose-custom a {{ color: #38bdf8; text-decoration: underline; }}
        .prose-custom strong {{ color: #ffffff; }}
        .prose-custom ul {{ list-style-type: disc; padding-left: 1.5rem; margin-bottom: 1rem; color: #cbd5e1; }}
        .prose-custom li {{ margin-bottom: 0.5rem; line-height: 1.6; color: #cbd5e1; }}
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #030712; }}
        ::-webkit-scrollbar-thumb {{ background: #1f2937; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #374151; }}

        /* Tema editorial claro: mantém os destaques em azul e melhora a leitura. */
        body {{
            background: #f8fafc !important;
            color: #0f172a !important;
        }}
        header {{
            background: rgba(255, 255, 255, 0.94) !important;
            border-color: #e2e8f0 !important;
        }}
        header .text-white, header a.text-white {{
            color: #0f172a !important;
        }}
        header .text-slate-400 {{ color: #64748b !important; }}
        header .bg-slate-900 {{
            background: #f1f5f9 !important;
            border-color: #cbd5e1 !important;
            color: #334155 !important;
        }}
        header input {{
            background: #f8fafc !important;
            border-color: #cbd5e1 !important;
            color: #0f172a !important;
        }}
        header input::placeholder {{ color: #94a3b8 !important; }}
        main {{ color: #334155; }}
        .noticia-card, #secaoDestaque > div {{
            background: #ffffff !important;
            border-color: #e2e8f0 !important;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.07) !important;
        }}
        .noticia-card:hover {{
            border-color: #93c5fd !important;
            box-shadow: 0 18px 36px rgba(37, 99, 235, 0.13) !important;
        }}
        .noticia-card .text-white, #secaoDestaque .text-white {{
            color: #0f172a !important;
        }}
        .noticia-card .text-slate-400, #secaoDestaque .text-slate-400 {{
            color: #64748b !important;
        }}
        .noticia-card .border-slate-800\/80 {{
            border-color: #e2e8f0 !important;
        }}
        #secaoDestaque .bg-slate-950 {{
            background: #e2e8f0 !important;
        }}
        #secaoDestaque .bg-gradient-to-t {{
            opacity: 0.55;
        }}
        #secaoDestaque .bg-gradient-to-r {{
            opacity: 0.5;
        }}
        #secaoDestaque .text-slate-200 {{ color: #475569 !important; }}
        #secaoDestaque .text-indigo-300 {{ color: #2563eb !important; }}
        #secaoDestaque .text-cyan-300 {{ color: #0369a1 !important; }}
        body > div.border-b.bg-slate-950\/60 {{
            background: #ffffff !important;
            border-color: #e2e8f0 !important;
        }}
        body > div.border-b.bg-slate-950\/60 .text-slate-500 {{
            color: #64748b !important;
        }}
        body > div.border-b.bg-slate-950\/60 .bg-slate-900 {{
            background: #f8fafc !important;
            border-color: #cbd5e1 !important;
            color: #475569 !important;
        }}
        #modalNoticia > div {{
            background: #ffffff !important;
            border-color: #e2e8f0 !important;
        }}
        #modalNoticia .text-white {{ color: #0f172a !important; }}
        #modalNoticia .bg-slate-900\/90 {{ background: #ffffff !important; }}
    </style>
</head>
<body class="min-h-screen flex flex-col selection:bg-indigo-500 selection:text-white bg-[#030712]">

    <!-- Barra de Status -->
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
                <span class="hidden sm:inline">📊 <strong>{qtd_total}</strong> artigos publicados</span>
            </div>
        </div>
    </div>

    <!-- Header / Navbar -->
    <header class="sticky top-0 z-40 bg-[#030712]/90 backdrop-blur-xl border-b border-slate-800/80">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30 font-black text-xl text-white">V</div>
                <div>
                    <a href="index.html" class="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                        VIEIRA<span class="text-indigo-400 font-extrabold">NEWS</span>
                        <span class="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30">AI Portal</span>
                    </a>
                    <p class="text-[11px] text-slate-400">Portal de Notícias em Tempo Real &amp; Curadoria com IA</p>
                </div>
            </div>
            <div class="w-full md:w-auto flex-1 max-w-md">
                <div class="relative">
                    <input type="text" id="campoBusca" placeholder="Pesquisar notícias por palavras-chave..."
                           class="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 pl-10 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all">
                    <svg class="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                    </svg>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <a href="https://github.com/Davi-vieira/Vieira_news" target="_blank" rel="noopener noreferrer"
                   class="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 text-xs font-semibold transition-all flex items-center gap-2">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>
                    <span>Repositório</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Barra de Filtros de Categorias -->
    <div class="border-b border-slate-900 bg-slate-950/60 py-3">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center space-x-2 overflow-x-auto">
            <span class="text-xs text-slate-500 font-semibold uppercase tracking-wider mr-2 shrink-0">Categorias:</span>
            <button onclick="filtrarCategoria('todas')" class="btn-filtro active px-3.5 py-1 rounded-full text-xs font-semibold bg-indigo-600 text-white transition-all shrink-0">Todas ({qtd_total})</button>
            <button onclick="filtrarCategoria('Inteligência Artificial')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">🤖 Inteligência Artificial</button>
            <button onclick="filtrarCategoria('Segurança Digital')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">🔒 Segurança Digital</button>
            <button onclick="filtrarCategoria('Carreira & Negócios')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">💼 Carreira & Negócios</button>
            <button onclick="filtrarCategoria('Tecnologia')" class="btn-filtro px-3.5 py-1 rounded-full text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-all shrink-0">⚡ Tecnologia Geral</button>
        </div>
    </div>
"""


def _html_hero(destaque: Dict[str, Any]) -> str:
    """Renderiza o bloco hero (destaque principal) — exclusivo da página 1."""
    if not destaque:
        return """
        <div class="rounded-3xl bg-slate-900/60 border border-slate-800 p-12 text-center my-8">
            <h3 class="text-xl font-bold text-white mb-2">Nenhuma notícia encontrada</h3>
            <p class="text-slate-400 max-w-md mx-auto text-sm">Execute a Fase 3 para coletar e persistir novas matérias no banco de dados <code>portal.db</code>.</p>
        </div>"""

    return f"""
    <div class="relative overflow-hidden rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl transition-all duration-300 hover:border-indigo-500/50 group mb-12">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-0">
            <div class="lg:col-span-7 relative h-72 sm:h-96 lg:h-auto overflow-hidden bg-slate-950">
                <img src="{destaque["imagem_url"]}" alt="{html.escape(destaque["titulo"])}"
                     class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105 opacity-90 group-hover:opacity-100"
                     onerror="this.src='https://picsum.photos/800/450?grayscale'" />
                <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-slate-900"></div>
                <div class="absolute top-4 left-4 flex items-center flex-wrap gap-2">
                    <span class="px-3 py-1 text-xs font-bold uppercase tracking-wider bg-rose-600/90 text-white rounded-full backdrop-blur-md shadow-lg flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-white animate-ping"></span>
                        Destaque Principal
                    </span>
                    <span class="px-3 py-1 text-xs font-semibold bg-slate-900/80 text-cyan-300 rounded-full border border-cyan-500/30 backdrop-blur-md">
                        {destaque["categoria"]}
                    </span>
                    <span class="px-3 py-1 text-xs font-semibold bg-slate-900/80 text-amber-300 rounded-full border border-amber-500/30 backdrop-blur-md">
                        📡 {destaque["fonte_nome"]}
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
                    <button onclick="abrirModal('{destaque["slug"]}')"
                            class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-semibold text-sm shadow-lg shadow-indigo-600/30 hover:shadow-indigo-500/50 transition-all flex items-center gap-2 cursor-pointer">
                        <span>Ler Notícia Completa</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                    </button>
                    <a href="{destaque["fonte_url"]}" target="_blank" rel="noopener noreferrer"
                       class="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-sm border border-slate-700 transition-all flex items-center gap-2">
                        <span>Fonte Original</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                </div>
            </div>
        </div>
    </div>"""


def _html_cards(noticias_pagina: List[Dict[str, Any]]) -> str:
    """Renderiza o grid de cards para a lista de notícias da página atual."""
    if not noticias_pagina:
        return '<p class="col-span-full text-center text-slate-500 py-6">Nenhuma notícia nesta página.</p>'

    cards = ""
    for noticia in noticias_pagina:
        cards += f"""
        <article class="noticia-card flex flex-col bg-slate-900 border border-slate-800/80 rounded-2xl overflow-hidden hover:border-indigo-500/40 hover:shadow-xl hover:shadow-indigo-500/5 transition-all duration-300 group"
                 data-categoria="{noticia["categoria"]}" data-titulo="{html.escape(noticia["titulo"].lower())}">
            <div class="relative h-48 overflow-hidden bg-slate-950">
                <img src="{noticia["imagem_url"]}" alt="{html.escape(noticia["titulo"])}"
                     class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 opacity-90 group-hover:opacity-100"
                     loading="lazy" onerror="this.src='https://picsum.photos/400/250?grayscale'" />
                <div class="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/20 to-transparent"></div>
                <div class="absolute top-3 left-3 flex items-center gap-1.5 flex-wrap">
                    <span class="px-2.5 py-0.5 text-xs font-semibold bg-slate-900/90 text-cyan-300 rounded-full border border-cyan-500/30 backdrop-blur-md">
                        {noticia["categoria"]}
                    </span>
                    <span class="px-2.5 py-0.5 text-xs font-semibold bg-slate-900/90 text-amber-300 rounded-full border border-amber-500/30 backdrop-blur-md">
                        📡 {noticia["fonte_nome"]}
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
                    <button onclick="abrirModal('{noticia["slug"]}')"
                            class="text-indigo-400 hover:text-indigo-300 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer">
                        <span>Ler síntese</span>
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                    </button>
                    <a href="{noticia["fonte_url"]}" target="_blank" rel="noopener noreferrer"
                       class="text-slate-400 hover:text-white text-xs font-medium bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1">
                        <span>Fonte</span>
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                </div>
            </div>
        </article>"""
    return cards


def _html_paginacao(pagina_atual: int, total_paginas: int) -> str:
    """
    Renderiza o componente de navegação de páginas com:
    - Botão 'Anterior' (desabilitado na página 1)
    - Numeração clicável com destaque na página atual
    - Botão 'Próxima' (desabilitado na última página)
    """
    if total_paginas <= 1:
        return ""

    anterior_url = nome_arquivo_pagina(pagina_atual - 1) if pagina_atual > 1 else None
    proxima_url  = nome_arquivo_pagina(pagina_atual + 1) if pagina_atual < total_paginas else None

    btn_anterior = (
        f'<a href="{anterior_url}" class="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 text-sm font-semibold transition-all">'
        '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>'
        'Anterior</a>'
        if anterior_url else
        '<span class="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900/40 text-slate-600 border border-slate-800/50 text-sm font-semibold cursor-not-allowed">'
        '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>'
        'Anterior</span>'
    )

    btn_proxima = (
        f'<a href="{proxima_url}" class="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-600 text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all">'
        'Próxima'
        '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>'
        '</a>'
        if proxima_url else
        '<span class="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900/40 text-slate-600 border border-slate-800/50 text-sm font-semibold cursor-not-allowed">'
        'Próxima'
        '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>'
        '</span>'
    )

    # Numeração: exibe até 5 páginas ao redor da atual (janela deslizante)
    janela = 2
    inicio = max(1, pagina_atual - janela)
    fim    = min(total_paginas, pagina_atual + janela)

    nums_html = ""
    if inicio > 1:
        nums_html += f'<a href="index.html" class="w-9 h-9 flex items-center justify-center rounded-xl text-sm font-semibold bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-all">1</a>'
        if inicio > 2:
            nums_html += '<span class="w-9 h-9 flex items-center justify-center text-slate-600 text-sm">…</span>'

    for p in range(inicio, fim + 1):
        url = nome_arquivo_pagina(p)
        if p == pagina_atual:
            nums_html += (
                f'<span class="w-9 h-9 flex items-center justify-center rounded-xl text-sm font-bold '
                f'bg-indigo-600 text-white border border-indigo-500 shadow-lg shadow-indigo-600/30">{p}</span>'
            )
        else:
            nums_html += (
                f'<a href="{url}" class="w-9 h-9 flex items-center justify-center rounded-xl text-sm font-semibold '
                f'bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-all">{p}</a>'
            )

    if fim < total_paginas:
        if fim < total_paginas - 1:
            nums_html += '<span class="w-9 h-9 flex items-center justify-center text-slate-600 text-sm">…</span>'
        ultima_url = nome_arquivo_pagina(total_paginas)
        nums_html += (
            f'<a href="{ultima_url}" class="w-9 h-9 flex items-center justify-center rounded-xl text-sm font-semibold '
            f'bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-all">{total_paginas}</a>'
        )

    return f"""
    <div class="flex flex-col items-center gap-4 mt-12 mb-4">
        <!-- Info de página -->
        <p class="text-xs text-slate-500">
            Página <strong class="text-slate-300">{pagina_atual}</strong> de <strong class="text-slate-300">{total_paginas}</strong>
        </p>
        <!-- Controles de navegação -->
        <div class="flex items-center gap-2 flex-wrap justify-center">
            {btn_anterior}
            <div class="flex items-center gap-1.5">
                {nums_html}
            </div>
            {btn_proxima}
        </div>
    </div>"""


def _html_modal_e_footer(noticias_json_safe: str, ano_atual: int) -> str:
    """Renderiza o modal de leitura, o footer e os scripts de interatividade."""
    return f"""
    <!-- Modal de Leitura Completa -->
    <div id="modalNoticia" class="fixed inset-0 z-50 hidden overflow-y-auto bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 transition-all duration-300">
        <div class="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
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
            <div class="p-6 sm:p-8 overflow-y-auto flex-1 prose-custom" id="modalCorpo"></div>
            <div class="p-4 sm:p-6 border-t border-slate-800 bg-slate-950 flex flex-wrap items-center justify-between gap-3">
                <span class="text-xs text-slate-500">Curado via Gemini IA</span>
                <div class="flex items-center space-x-3">
                    <button onclick="fecharModal()" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition-colors">Fechar</button>
                    <a id="modalLinkOriginal" href="#" target="_blank" rel="noopener noreferrer"
                       class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-1.5">
                        <span>Acessar Matéria Completa no Portal Oficial</span>
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="border-t border-slate-800 bg-slate-950 text-slate-400 py-12 mt-16">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
                <div class="md:col-span-2">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 flex items-center justify-center font-black text-sm text-white">V</div>
                        <span class="text-xl font-bold text-white">Vieira News</span>
                    </div>
                    <p class="text-sm text-slate-400 leading-relaxed max-w-sm mb-4">
                        Portal moderno de notícias com pipeline 100% automatizado: coleta RSS multicanal, curadoria com Inteligência Artificial e publicação estática contínua via GitHub Actions.
                    </p>
                    <div class="flex flex-wrap gap-2">
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">Python 3.12</span>
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">Google Gemini IA</span>
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">Tailwind CSS</span>
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">GitHub Actions</span>
                        <span class="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 text-slate-300 border border-slate-800">SQLite</span>
                    </div>
                </div>
                <div>
                    <h5 class="text-xs font-bold uppercase tracking-wider text-slate-200 mb-4">Etapas do Pipeline</h5>
                    <ul class="space-y-2 text-xs text-slate-400">
                        <li><span class="text-indigo-400 font-semibold">Fase 1:</span> Coleta RSS Multicanal</li>
                        <li><span class="text-indigo-400 font-semibold">Fase 2:</span> Curadoria com Gemini IA</li>
                        <li><span class="text-indigo-400 font-semibold">Fase 3:</span> Persistência Relacional (SQLite)</li>
                        <li><span class="text-indigo-400 font-semibold">Fase 4:</span> Frontend Static Builder</li>
                        <li><span class="text-indigo-400 font-semibold">Fase 5:</span> Paginação Estática</li>
                    </ul>
                </div>
                <div>
                    <h5 class="text-xs font-bold uppercase tracking-wider text-slate-200 mb-4">Links &amp; Créditos</h5>
                    <ul class="space-y-2 text-xs text-slate-400">
                        <li><a href="https://github.com/Davi-vieira/Vieira_news" target="_blank" class="hover:text-white transition-colors">Repositório no GitHub ↗</a></li>
                        <li><a href="https://g1.globo.com/tecnologia/" target="_blank" class="hover:text-white transition-colors">G1 Tecnologia ↗</a></li>
                        <li><a href="https://canaltech.com.br" target="_blank" class="hover:text-white transition-colors">Canaltech ↗</a></li>
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

    <!-- Scripts de Interatividade -->
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
            document.getElementById('modalNoticia').classList.add('hidden');
            document.body.style.overflow = 'auto';
        }}

        document.getElementById('modalNoticia').addEventListener('click', function(e) {{
            if (e.target === this) fecharModal();
        }});

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') fecharModal();
        }});

        // Filtragem por busca e categorias
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
                if (bateCategoria && bateBusca) {{ card.style.display = 'flex'; visiveis++; }}
                else {{ card.style.display = 'none'; }}
            }});
            const semResultados = document.getElementById('semResultados');
            const contador = document.getElementById('contadorResultados');
            if (visiveis === 0 && cards.length > 0) {{ semResultados.classList.remove('hidden'); }}
            else {{ semResultados.classList.add('hidden'); }}
            contador.innerText = `Exibindo ${{visiveis}} matéria(s)`;
        }}

        campoBusca.addEventListener('input', aplicarFiltros);
    </script>
</body>
</html>"""


# ─── Função principal de construção ───────────────────────────────────────────

def construir_site(
    db_path: str = "portal.db",
    pasta_destino: str = "public",
    noticias_por_pagina: int = NOTICIAS_POR_PAGINA,
) -> List[Path]:
    """
    Lê todas as matérias do banco SQLite, divide em páginas e gera os arquivos HTML:
      - public/index.html     → página 1 (com Hero section)
      - public/pagina_2.html  → página 2 (apenas grid)
      - public/pagina_N.html  → ...

    Args:
        db_path (str): Caminho do banco de dados SQLite.
        pasta_destino (str): Pasta de saída dos arquivos estáticos.
        noticias_por_pagina (int): Quantidade de cards no grid por página.

    Returns:
        List[Path]: Lista de caminhos dos arquivos HTML gerados.
    """
    print("\n" + "=" * 80)
    print(" INICIANDO FASE 4 (ETAPA 6): CONSTRUTOR COM PAGINAÇÃO ESTÁTICA")
    print("=" * 80)

    caminho_public = Path.cwd() / pasta_destino
    caminho_public.mkdir(parents=True, exist_ok=True)

    # 1. Carrega todas as notícias do banco
    todas_noticias = carregar_noticias_do_banco(db_path=db_path)
    qtd_total      = len(todas_noticias)
    ano_atual      = datetime.now().year
    agora_fmt      = formatar_data_pt(datetime.now())

    if not todas_noticias:
        print("[!] Nenhuma notícia no banco. Gerando index.html vazio.")
        total_paginas = 1
    else:
        # Página 1 usa 1 notícia para o hero + noticias_por_pagina no grid.
        # Páginas 2+ só são necessárias quando esse limite é ultrapassado.
        noticias_excedentes = max(0, len(todas_noticias) - 1 - noticias_por_pagina)
        total_paginas = 1 + math.ceil(noticias_excedentes / noticias_por_pagina)

    print(f"\n[+] {qtd_total} notícia(s) | {noticias_por_pagina} por página | {total_paginas} página(s) a gerar.")

    # Serializa TODAS as notícias em JSON (para modal JS em qualquer página)
    noticias_json_safe = json.dumps(
        [{
            "slug":          n["slug"],
            "titulo":        n["titulo"],
            "imagem_url":    n["imagem_url"],
            "resumo_texto":  n["resumo_texto"],
            "categoria":     n["categoria"],
            "tempo_leitura": n["tempo_leitura"],
            "data_formatada":n["data_formatada"],
            "fonte_url":     n["fonte_url"],
            "fonte_nome":    n["fonte_nome"],
            "html_completo": n["html_completo"],
        } for n in todas_noticias],
        ensure_ascii=False,
    )

    arquivos_gerados: List[Path] = []

    for pagina_num in range(1, total_paginas + 1):
        eh_index = pagina_num == 1
        nome_arq = nome_arquivo_pagina(pagina_num)

        # Fatia das notícias do grid para esta página
        if eh_index:
            destaque        = todas_noticias[0] if todas_noticias else None
            noticias_grid   = todas_noticias[1:1 + noticias_por_pagina]
        else:
            destaque        = None
            offset          = 1 + (pagina_num - 2) * noticias_por_pagina + noticias_por_pagina
            noticias_grid   = todas_noticias[offset: offset + noticias_por_pagina]

        titulo_aba = (
            "Vieira News | Portal de Notícias Inteligente"
            if eh_index else
            f"Vieira News | Página {pagina_num}"
        )

        # Monta o HTML da página
        corpo_main = ""
        if eh_index:
            corpo_main += f"""
    <!-- Hero: Destaque Principal (exclusivo do index.html) -->
    <div id="secaoDestaque">
        {_html_hero(destaque)}
    </div>"""

        corpo_main += f"""
    <!-- Cabeçalho do grid -->
    <div class="flex items-center justify-between mb-6">
        <div class="flex items-center space-x-2">
            <div class="w-2.5 h-6 bg-indigo-500 rounded-full"></div>
            <h3 class="text-xl font-extrabold text-white tracking-tight">
                {"Últimas Notícias Curadas" if eh_index else f"Notícias — Página {pagina_num}"}
            </h3>
        </div>
        <span class="text-xs text-slate-400 font-medium" id="contadorResultados">Exibindo todas as matérias</span>
    </div>

    <!-- Grid de Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="gridNoticias">
        {_html_cards(noticias_grid)}
    </div>

    <!-- Sem resultados na busca -->
    <div id="semResultados" class="hidden text-center py-16 bg-slate-900/30 rounded-3xl border border-slate-800/80 my-8">
        <div class="w-12 h-12 bg-slate-800 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        </div>
        <h4 class="text-lg font-bold text-white mb-1">Nenhuma notícia encontrada</h4>
        <p class="text-sm text-slate-400">Tente buscar por outro termo ou limpar os filtros de categoria.</p>
    </div>

    <!-- Navegação de Páginas -->
    {_html_paginacao(pagina_num, total_paginas)}
"""

        html_completo = (
            _html_cabecalho(titulo_aba, agora_fmt, qtd_total)
            + f'\n    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">\n'
            + corpo_main
            + "\n    </main>\n"
            + _html_modal_e_footer(noticias_json_safe, ano_atual)
        )

        arquivo = caminho_public / nome_arq
        arquivo.write_text(html_completo, encoding="utf-8")
        tamanho_kb = len(html_completo.encode("utf-8")) / 1024
        print(f"  [✓] {nome_arq:20s} → {len(noticias_grid):2d} cards | {tamanho_kb:.1f} KB")
        arquivos_gerados.append(arquivo)

    print("\n" + "=" * 80)
    print(f"[OK] {len(arquivos_gerados)} arquivo(s) HTML gerado(s) com paginação estática!")
    print(f"     Pasta: {caminho_public.resolve()}")
    print(f"     Para testar: python -m http.server 8000 --directory public")
    print("=" * 80 + "\n")

    return arquivos_gerados


if __name__ == "__main__":
    construir_site()

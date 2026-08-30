"""
MÓDULO: Banco de Dados Relacional (SQLite) - Portal Vieira News
OBJETIVO: Gerenciar a persistência estruturada das notícias curadas no banco 'portal.db'.
          Substitui o armazenamento em arquivos físicos por uma tabela relacional otimizada,
          com suporte a serialização/deserialização JSON de arrays e prevenção de duplicatas por slug.
"""

import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_NAME_PADRAO = "portal.db"


def sanitizar_slug(texto: str, max_caracteres: int = 60) -> str:
    """
    Gera um slug único e limpo a partir de um título:
    - Converte para minúsculas;
    - Remove acentos e caracteres especiais;
    - Substitui espaços por hifens.
    """
    texto_sem_acento = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    texto_limpo = re.sub(r"[^a-zA-Z0-9\s-]", "", texto_sem_acento).lower().strip()
    slug = re.sub(r"[\s_]+", "-", texto_limpo)
    slug = slug[:max_caracteres].rstrip("-")
    return slug or "noticia"


def obter_conexao(db_path: str = DB_NAME_PADRAO) -> sqlite3.Connection:
    """
    Cria e retorna uma conexão configurada com o banco SQLite.
    """
    caminho = Path(db_path)
    conexao = sqlite3.connect(str(caminho))
    conexao.row_factory = sqlite3.Row  # Permite acesso às colunas como dicionário
    return conexao


def inicializar_banco(db_path: str = DB_NAME_PADRAO) -> None:
    """
    Cria a tabela 'noticias' no banco de dados SQLite caso ainda não exista.
    
    Colunas:
        id: Identificador único autoincrementável.
        slug: Identificador textual único da matéria (evita duplicações).
        titulo: Título da notícia curada pela IA.
        resumo: Texto de resumo da matéria.
        pontos_principais: Lista de bullet points serializada em JSON.
        impacto: Conclusão e análise de impacto do fato.
        imagem_url: Link absoluto da imagem oficial extraída.
        link_original: URL da fonte primária da matéria.
        categoria: Categoria editorial atribuída.
        data_criacao: Timestamp ISO da data de registro.
    """
    ddl_tabela = """
    CREATE TABLE IF NOT EXISTS noticias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        resumo TEXT,
        pontos_principais TEXT,
        impacto TEXT,
        imagem_url TEXT,
        link_original TEXT,
        categoria TEXT,
        data_criacao TEXT NOT NULL
    );
    """
    with obter_conexao(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(ddl_tabela)
        # Índice auxiliar para buscas rápidas por data e slug
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_noticias_data ON noticias(data_criacao DESC);")
        conn.commit()


def inserir_noticia(noticia: Dict[str, Any], db_path: str = DB_NAME_PADRAO) -> bool:
    """
    Insere uma notícia no banco de dados, evitando duplicatas com base no slug.
    Serializa a lista 'pontos_principais' para formato JSON.

    Args:
        noticia (Dict[str, Any]): Dicionário com os dados da matéria curada.
        db_path (str): Caminho do banco SQLite.

    Returns:
        bool: True se a notícia foi inserida com sucesso; False se já existia (duplicata).
    """
    inicializar_banco(db_path)

    titulo = noticia.get("titulo_curado") or noticia.get("titulo") or "Sem Título"
    slug = noticia.get("slug") or sanitizar_slug(titulo)
    resumo = noticia.get("resumo") or ""
    impacto = noticia.get("impacto") or ""
    imagem_url = noticia.get("imagem_url") or ""
    link_original = noticia.get("link") or noticia.get("link_original") or ""
    categoria = noticia.get("categoria") or "Tecnologia"
    data_criacao = noticia.get("data_criacao") or datetime.now().isoformat()

    # Serialização da lista de pontos principais em string JSON
    pontos_principais = noticia.get("pontos_principais", [])
    if isinstance(pontos_principais, list):
        pontos_json = json.dumps(pontos_principais, ensure_ascii=False)
    elif isinstance(pontos_principais, str):
        pontos_json = pontos_principais
    else:
        pontos_json = json.dumps([], ensure_ascii=False)

    sql = """
    INSERT INTO noticias (
        slug, titulo, resumo, pontos_principais, impacto,
        imagem_url, link_original, categoria, data_criacao
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(slug) DO NOTHING;
    """

    with obter_conexao(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (
            slug,
            titulo,
            resumo,
            pontos_json,
            impacto,
            imagem_url,
            link_original,
            categoria,
            data_criacao
        ))
        conn.commit()
        inserido = cursor.rowcount > 0

    return inserido


def salvar_lote_noticias(noticias: List[Dict[str, Any]], db_path: str = DB_NAME_PADRAO) -> int:
    """
    Salva uma lista de notícias no banco de dados SQLite em lote.

    Args:
        noticias (List[Dict[str, Any]]): Lista de dicionários de notícias da Fase 2.
        db_path (str): Caminho do banco SQLite.

    Returns:
        int: Quantidade de notícias novas inseridas com sucesso.
    """
    if not noticias:
        return 0

    inicializar_banco(db_path)
    novas_inseridas = 0

    for noticia in noticias:
        if inserir_noticia(noticia, db_path=db_path):
            novas_inseridas += 1

    return novas_inseridas


def listar_noticias(db_path: str = DB_NAME_PADRAO, limite: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Consulta todas as notícias salvas no banco de dados, ordenadas da mais recente para a mais antiga.
    Converte a string JSON da coluna 'pontos_principais' de volta para uma lista Python nativa.

    Args:
        db_path (str): Caminho do banco SQLite.
        limite (Optional[int]): Quantidade máxima de registros a retornar.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários representando as matérias cadastradas.
    """
    inicializar_banco(db_path)

    sql = "SELECT * FROM noticias ORDER BY data_criacao DESC, id DESC"
    if limite and isinstance(limite, int) and limite > 0:
        sql += f" LIMIT {limite}"

    resultado = []
    with obter_conexao(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        linhas = cursor.fetchall()

        for linha in linhas:
            dados = dict(linha)

            # Deserializa a coluna pontos_principais de JSON para lista Python
            pontos_raw = dados.get("pontos_principais")
            if pontos_raw:
                try:
                    dados["pontos_principais"] = json.loads(pontos_raw)
                except Exception:
                    dados["pontos_principais"] = [pontos_raw]
            else:
                dados["pontos_principais"] = []

            resultado.append(dados)

    return resultado


def contar_noticias(db_path: str = DB_NAME_PADRAO) -> int:
    """
    Retorna o número total de matérias cadastradas no banco de dados.
    """
    inicializar_banco(db_path)
    with obter_conexao(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM noticias;")
        total = cursor.fetchone()[0]
    return total


if __name__ == "__main__":
    print("[+] Testando inicialização e operações em banco_dados.py...")
    inicializar_banco()
    total = contar_noticias()
    print(f"[OK] Banco 'portal.db' inicializado com sucesso! Total de notícias cadastradas: {total}.")

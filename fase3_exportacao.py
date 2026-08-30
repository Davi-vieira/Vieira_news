"""
MÓDULO: Fase 3 - Persistência Relacional (SQLite)
OBJETIVO: Receber as notícias curadas pela IA na Fase 2 e persistir diretamente no banco
          de dados relacional 'portal.db' utilizando o módulo banco_dados.py.
          Substitui a antiga geração de arquivos .md em disco por uma base SQL estruturada.
"""

import sys
from typing import Any, Dict, List

# Garante suporte a caracteres UTF-8 no terminal do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Importa o gerenciador do banco de dados e o orquestrador da Fase 2
from banco_dados import contar_noticias, inicializar_banco, salvar_lote_noticias
from fase2_geracao_ia import processar_fluxo_completo


def exportar_noticias_para_banco(
    artigos: List[Dict[str, Any]], db_path: str = "portal.db"
) -> int:
    """
    Persiste uma lista de artigos curados diretamente na tabela 'noticias' do banco SQLite.
    Evita duplicações automáticas através do slug único de cada notícia.

    Args:
        artigos (List[Dict[str, Any]]): Lista de notícias curadas retornadas pela Fase 2.
        db_path (str): Caminho do banco SQLite (padrão: portal.db).

    Returns:
        int: Quantidade de registros novos gravados com sucesso.
    """
    if not artigos:
        print("[!] Nenhum artigo recebido para persistência no banco de dados.")
        return 0

    print(f"\n[+] Persistindo {len(artigos)} artigo(s) no banco relacional '{db_path}'...")
    novos_inseridos = salvar_lote_noticias(artigos, db_path=db_path)
    total_banco = contar_noticias(db_path=db_path)

    print(f"  [✓] {novos_inseridos} nova(s) matéria(s) gravada(s) com sucesso no SQLite.")
    print(f"  [✓] Total acumulado no banco de dados: {total_banco} notícia(s).")

    return novos_inseridos


def executar_fase3():
    """
    Fluxo principal da Fase 3: Executa o pipeline completo (Fase 1 -> Fase 2 -> Fase 3 SQLite).
    """
    print("\n" + "=" * 80)
    print(" INICIANDO PIPELINE: FASE 1 -> FASE 2 -> FASE 3 (BANCO DE DADOS SQLITE)")
    print("=" * 80)

    # 1. Garante que o banco de dados e as tabelas estejam inicializados
    inicializar_banco()

    # 2. Executa a Fase 1 (Coleta RSS) + Fase 2 (Curadoria com Gemini IA)
    artigos_curados = processar_fluxo_completo(limite_noticias=3, feed_chave="g1_tecnologia")

    if not artigos_curados:
        print("[!] Nenhum novo artigo inédito retornado para persistência.")
        print(f"    Total de notícias mantidas no banco: {contar_noticias()}.")
        return

    # 3. Executa a Fase 3 (Gravação direta no SQLite)
    novos_registros = exportar_noticias_para_banco(artigos_curados)

    print("\n" + "=" * 80)
    print(f"[OK] Fase 3 concluída com sucesso! {novos_registros} novo(s) registro(s) no SQLite.")
    print(f"     Banco de Dados: portal.db (Total geral: {contar_noticias()} registros)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    executar_fase3()

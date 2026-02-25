#!/usr/bin/env python3
"""
Gerenciador de Contextos RLM

Salva, carrega e gerencia históricos de usuários e contextos
para uso com o RLM.
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path


class ContextoManager:
    """Gerencia arquivos de contexto para RLM."""
    
    def __init__(self, base_dir: str = "rlm/contextos"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def salvar_historico(self, user_id: str, historico: str, metadata: dict = None) -> str:
        """
        Salva um histórico de usuário.
        
        Args:
            user_id: ID do usuário (ex: 'usuario_123')
            historico: Texto do histórico/contexto
            metadata: Dicionário com metadados (autor, tipo, etc)
        
        Returns:
            Caminho do arquivo salvo
        """
        filename = f"{user_id}_historico.txt"
        filepath = self.base_dir / filename
        
        # Salva o histórico
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(historico)
        
        # Salva metadata se fornecida
        if metadata:
            meta_filepath = self.base_dir / f"{user_id}_metadata.json"
            metadata['timestamp'] = datetime.now().isoformat()
            metadata['file_size'] = len(historico)
            with open(meta_filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Histórico salvo: {filepath}")
        return str(filepath)
    
    def carregar_historico(self, user_id: str) -> str:
        """Carrega um histórico de usuário."""
        filepath = self.base_dir / f"{user_id}_historico.txt"
        
        if not filepath.exists():
            raise FileNotFoundError(f"Histórico não encontrado: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def salvar_contexto_arquivo(self, nome: str, conteudo: str) -> str:
        """
        Salva um arquivo de contexto (log, código, etc).
        
        Args:
            nome: Nome do arquivo (ex: 'erro_deploy.log')
            conteudo: Conteúdo do arquivo
        
        Returns:
            Caminho do arquivo salvo
        """
        filepath = self.base_dir / nome
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print(f"✓ Contexto salvo: {filepath}")
        return str(filepath)
    
    def listar_contextos(self) -> list:
        """Lista todos os contextos disponíveis."""
        if not self.base_dir.exists():
            return []
        
        contextos = []
        for filepath in sorted(self.base_dir.glob("*_historico.txt")):
            size = filepath.stat().st_size
            contextos.append({
                'arquivo': filepath.name,
                'tamanho': f"{size / 1024:.2f} KB",
                'caminho': str(filepath)
            })
        
        return contextos
    
    def limpar_contexto(self, user_id: str) -> bool:
        """Remove um contexto de usuário."""
        filepath = self.base_dir / f"{user_id}_historico.txt"
        meta_filepath = self.base_dir / f"{user_id}_metadata.json"
        
        removidos = []
        for f in [filepath, meta_filepath]:
            if f.exists():
                f.unlink()
                removidos.append(f.name)
        
        if removidos:
            print(f"✓ Removidos: {', '.join(removidos)}")
            return True
        else:
            print(f"⚠️  Nenhum arquivo encontrado para {user_id}")
            return False


# ============= CLI =============

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gerenciador de Contextos para RLM"
    )
    
    subparsers = parser.add_subparsers(dest="comando", help="Comando a executar")
    
    # Comando: salvar
    save_parser = subparsers.add_parser("salvar", help="Salvar histórico de usuário")
    save_parser.add_argument("--user-id", required=True, help="ID do usuário")
    save_parser.add_argument("--arquivo", required=True, help="Arquivo com o histórico")
    save_parser.add_argument("--tipo", default="chat", help="Tipo de histórico (chat, log, etc)")
    
    # Comando: carregar
    load_parser = subparsers.add_parser("carregar", help="Carregar histórico de usuário")
    load_parser.add_argument("--user-id", required=True, help="ID do usuário")
    load_parser.add_argument("--saida", help="Arquivo para salvar o resultado")
    
    # Comando: listar
    list_parser = subparsers.add_parser("listar", help="Listar todos os contextos")
    
    # Comando: limpar
    clean_parser = subparsers.add_parser("limpar", help="Remover contexto de usuário")
    clean_parser.add_argument("--user-id", required=True, help="ID do usuário")
    
    args = parser.parse_args()
    manager = ContextoManager()
    
    try:
        if args.comando == "salvar":
            if not os.path.isfile(args.arquivo):
                print(f"❌ Arquivo não encontrado: {args.arquivo}")
            else:
                with open(args.arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                
                metadata = {"tipo": args.tipo, "arquivo_origem": args.arquivo}
                manager.salvar_historico(args.user_id, conteudo, metadata)
        
        elif args.comando == "carregar":
            historico = manager.carregar_historico(args.user_id)
            if args.saida:
                with open(args.saida, 'w', encoding='utf-8') as f:
                    f.write(historico)
                print(f"✓ Salvo em: {args.saida}")
            else:
                print(historico)
        
        elif args.comando == "listar":
            contextos = manager.listar_contextos()
            if not contextos:
                print("Nenhum contexto encontrado")
            else:
                print(f"\n{'📋 CONTEXTOS DISPONÍVEIS':^60}")
                print("-" * 60)
                for ctx in contextos:
                    print(f"  {ctx['arquivo']:<40} {ctx['tamanho']:>15}")
                print(f"{'-' * 60}\nTotal: {len(contextos)} arquivo(s)\n")
        
        elif args.comando == "limpar":
            manager.limpar_contexto(args.user_id)
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        exit(1)

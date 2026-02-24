#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recursive Language Model (RLM) - Agente Generico via Ollama

Processa tarefas complexas de forma recursiva com poucos recursos.
Suporta analise de textos grandes, arquivos e historicos.
"""

import re
import sys
import io
import os
import argparse
import json
from ollama import Client


# ============= CONFIGURACAO =============
ollama_host = os.environ.get('OLLAMA_HOST', 'http://ollama:11434')
cliente_ollama = Client(host=ollama_host)


# ============= CLASSES GENERICAS =============

class LocalREPL:
    """
    Environment local para capturar outputs Python.
    Simula um REPL (Read-Eval-Print Loop) seguro.
    """
    def __init__(self):
        self.locals = {}
        self.output = io.StringIO()

    def execute(self, code: str) -> str:
        """Executa codigo Python e retorna o output."""
        try:
            old_stdout = sys.stdout
            sys.stdout = self.output
            exec(code, self.locals)
            sys.stdout = old_stdout
            return self.output.getvalue()
        except Exception as e:
            sys.stdout = old_stdout
            return f"[ERROR] {type(e).__name__}: {str(e)}"

    def clear(self):
        """Limpa o buffer de output."""
        self.output = io.StringIO()


class OllamaRLM:
    """
    Recursive Language Model usando Ollama.
    
    Funciona em etapas:
    1. Recebe uma tarefa complexa
    2. Quebra em sub-tarefas (thinking)
    3. Processa cada sub-tarefa
    4. Agrega os resultados
    5. Retorna resposta final
    """
    
    def __init__(self, model: str = "qwen3:4b"):
        self.model = model
        self.repl = LocalREPL()
        self.max_depth = 3
        self.call_count = 0

    def _sanitize_response(self, text: str) -> str:
        """Remove markdown code blocks e caracteres especiais."""
        text = re.sub(r'```(?:python|json|yaml|plaintext|)?\n?', '', text)
        text = re.sub(r'```', '', text)
        return text.strip()

    def _split_task(self, tarefa: str, contexto: str) -> list:
        """
        Quebra a tarefa em sub-tarefas recursivas.
        Retorna lista de sub-tarefas.
        """
        prompt = f"""Analise esta tarefa e quebre-a em 2-3 sub-tarefas menores.
Retorne APENAS JSON com chave "subtasks".

TAREFA: {tarefa}

CONTEXTO (primeiros 500 chars): {contexto[:500]}...

Responda APENAS em JSON:"""
        try:
            response = cliente_ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=False
            )
            
            text = response.get('response', '{}')
            text = self._sanitize_response(text)
            
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return data.get('subtasks', [tarefa])
            return [tarefa]
        except Exception as e:
            print(f"[!] Erro ao quebrar tarefa: {e}")
            return [tarefa]

    def _process_subtask(self, subtarefa: str, contexto: str) -> str:
        """Processa uma sub-tarefa individual."""
        prompt = f"""Resolva esta sub-tarefa de forma concisa.

TAREFA: {subtarefa}

CONTEXTO:
{contexto[:2000]}

Responda APENAS a solucao, sem explicacoes desnecessarias."""
        try:
            response = cliente_ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=False
            )
            return response.get('response', '').strip()
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _aggregate_results(self, subtarefas: list, resultados: list, tarefa_original: str) -> str:
        """Agrega os resultados das sub-tarefas em uma resposta final."""
        aggregation_prompt = f"""Agregue estes resultados em uma resposta coerente.

TAREFA ORIGINAL: {tarefa_original}

RESULTADOS:
"""
        for i, (sub, res) in enumerate(zip(subtarefas, resultados)):
            aggregation_prompt += f"\n[{i+1}] {sub}\n    -> {res[:500]}\n"

        aggregation_prompt += "\nRetorne uma resposta final clara:"

        try:
            response = cliente_ollama.generate(
                model=self.model,
                prompt=aggregation_prompt,
                stream=False
            )
            return response.get('response', '').strip()
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def chat_completion(self, tarefa: str, contexto: str = "") -> str:
        """
        Executa o fluxo RLM completo.
        
        Args:
            tarefa: Instrucao principal
            contexto: Texto de contexto (pode vir de arquivo ou direto)
        
        Returns:
            Resposta final processada
        """
        self.call_count += 1
        print(f"\n[RLM-{self.call_count}] Processing: {tarefa[:80]}...")

        # Step 1: Split task
        subtarefas = self._split_task(tarefa, contexto)
        print(f"[RLM] Split into {len(subtarefas)} subtasks")

        # Step 2: Process each subtask
        resultados = []
        for i, subtarefa in enumerate(subtarefas, 1):
            print(f"  [{i}/{len(subtarefas)}] {subtarefa[:60]}...")
            resultado = self._process_subtask(subtarefa, contexto)
            resultados.append(resultado)

        # Step 3: Aggregate results
        print("[RLM] Aggregating final results...")
        resposta_final = self._aggregate_results(subtarefas, resultados, tarefa)

        return resposta_final


# ============= MODO GENERICO (Ponto de Entrada) =============

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RLM Generico via Ollama - Processa tarefas complexas"
    )
    
    parser.add_argument(
        "--tarefa",
        type=str,
        required=True,
        help="Instrucao principal para o RLM"
    )
    
    parser.add_argument(
        "--contexto",
        type=str,
        default="",
        help="Texto de contexto ou caminho para arquivo"
    )
    
    parser.add_argument(
        "--modelo",
        type=str,
        default="qwen3:4b",
        help="Modelo Ollama a usar"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Modo verboso com mais detalhes"
    )

    args = parser.parse_args()

    # Step 1: Load context
    contexto_final = args.contexto
    
    if args.contexto and os.path.isfile(args.contexto):
        print(f"[*] Reading context from file: {args.contexto}")
        try:
            with open(args.contexto, 'r', encoding='utf-8') as f:
                contexto_final = f.read()
                print(f"[+] Loaded {len(contexto_final)} characters")
        except Exception as e:
            print(f"[-] Error reading file: {e}")
            sys.exit(1)
    elif args.contexto:
        print("[*] Using provided text as context")
    else:
        print("[!] No context provided (task only)")

    # Step 2: Initialize RLM
    print(f"\n[*] Starting RLM with model: {args.modelo}")
    try:
        rlm = OllamaRLM(model=args.modelo)
    except Exception as e:
        print(f"[-] Error initializing RLM: {e}")
        sys.exit(1)

    # Step 3: Execute
    print("\n" + "="*50)
    print(f"[TASK] {args.tarefa}")
    print("="*50)

    try:
        resultado_final = rlm.chat_completion(args.tarefa, contexto_final)
        
        print("\n" + "="*50)
        print("[+] FINAL RLM RESPONSE")
        print("="*50)
        print(resultado_final)
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[-] Fatal error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)

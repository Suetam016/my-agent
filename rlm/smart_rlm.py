#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart RLM - Versao com Early Exit

RLM por default, mas com ability de detectar quando a resposta
eh simples/obvia e retornar rapidamente sem processar full pipeline.
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


# ============= CLASSES =============

class LocalREPL:
    """Environment local para capturar outputs Python."""
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


class SmartRLM:
    """
    Smart Recursive Language Model com Early Exit.
    
    Processo:
    1. Tenta responder direto (FAST PATH)
    2. Se confiante 100%, retorna imediatamente
    3. Se nao confiante, vai pra SLOW PATH (RLM completo)
    """
    
    def __init__(self, model: str = "qwen3:4b"):
        self.model = model
        self.repl = LocalREPL()
        self.max_depth = 3
        self.call_count = 0
        self.confidence_threshold = 0.90  # 90% de confianca pra early exit

    def _sanitize_response(self, text: str) -> str:
        """Remove markdown code blocks e caracteres especiais."""
        text = re.sub(r'```(?:python|json|yaml|plaintext|)?\n?', '', text)
        text = re.sub(r'```', '', text)
        return text.strip()

    def _try_fast_path(self, tarefa: str, contexto: str) -> tuple:
        """
        Tenta responder RÁPIDO e retorna (resposta, confianca).
        
        Returns:
            (resposta, confianca) - confianca entre 0.0 e 1.0
        """
        prompt = f"""Responda esta pergunta RAPIDAMENTE e com CONFIANCA.
Se voce tem CERTEZA ABSOLUTA (100%) que sabe a resposta, responda direto.
Se tem duvida, responda com [UNCERTAIN] no inicio.

PERGUNTA: {tarefa}

CONTEXTO: {contexto[:500]}

Responda CONCISO:"""

        try:
            response = cliente_ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=False
            )
            
            resposta = response.get('response', '').strip()
            resposta = self._sanitize_response(resposta)
            
            # Detecta se modelo tem certeza
            if resposta.startswith('[UNCERTAIN]'):
                confianca = 0.5  # Baixa confianca
                resposta = resposta.replace('[UNCERTAIN]', '').strip()
                print("[FastPath] Low confidence -> vai pro RLM completo")
                return (resposta, confianca)
            else:
                confianca = 0.95  # Alta confianca
                print("[FastPath] High confidence (95%) -> retorna imediatamente!")
                return (resposta, confianca)
                
        except Exception as e:
            print(f"[!] Erro no fast path: {e}")
            return (None, 0.0)

    def _split_task(self, tarefa: str, contexto: str) -> list:
        """Quebra a tarefa em sub-tarefas."""
        prompt = f"""Analise esta tarefa e quebre-a em 2-3 sub-tarefas.
Retorne APENAS JSON com chave "subtasks".

TAREFA: {tarefa}
CONTEXTO (primeiros 500 chars): {contexto[:500]}...

JSON:"""
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
            print(f"[!] Erro ao quebrar: {e}")
            return [tarefa]

    def _process_subtask(self, subtarefa: str, contexto: str) -> str:
        """Processa uma sub-tarefa individual."""
        prompt = f"""Resolva esta sub-tarefa de forma concisa.

TAREFA: {subtarefa}

CONTEXTO:
{contexto[:2000]}

Resposta:"""
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
        """Agrega resultados das sub-tarefas."""
        aggregation_prompt = f"""Agregue estes resultados em uma resposta coerente.

TAREFA ORIGINAL: {tarefa_original}

RESULTADOS:
"""
        for i, (sub, res) in enumerate(zip(subtarefas, resultados)):
            aggregation_prompt += f"\n[{i+1}] {sub}\n    -> {res[:500]}\n"

        aggregation_prompt += "\nResposta final clara:"

        try:
            response = cliente_ollama.generate(
                model=self.model,
                prompt=aggregation_prompt,
                stream=False
            )
            return response.get('response', '').strip()
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _full_rlm(self, tarefa: str, contexto: str) -> str:
        """
        Executa o pipeline RLM COMPLETO.
        Eh chamado quando fast path nao teve confianca suficiente.
        """
        print("\n[RLM-Full] Iniciando pipeline completo...")
        
        # Step 1: Split
        subtarefas = self._split_task(tarefa, contexto)
        print(f"[RLM] Split em {len(subtarefas)} sub-tarefas")

        # Step 2: Process
        resultados = []
        for i, subtarefa in enumerate(subtarefas, 1):
            print(f"  [{i}/{len(subtarefas)}] {subtarefa[:60]}...")
            resultado = self._process_subtask(subtarefa, contexto)
            resultados.append(resultado)

        # Step 3: Aggregate
        print("[RLM] Agregando resultados...")
        resposta_final = self._aggregate_results(subtarefas, resultados, tarefa)

        return resposta_final

    def chat_completion(self, tarefa: str, contexto: str = "") -> dict:
        """
        Executa Smart RLM com Early Exit.
        
        Returns:
            {
                'resposta': str,
                'confianca': float,
                'modo': 'fast' ou 'full',
                'tempo_ms': int
            }
        """
        import time
        start_time = time.time()
        
        self.call_count += 1
        print(f"\n[SmartRLM-{self.call_count}] Processando: {tarefa[:80]}...")

        # STEP 1: FAST PATH
        print("[*] Tentando resposta rápida...")
        resposta_fast, confianca = self._try_fast_path(tarefa, contexto)

        # DECISION POINT
        if confianca >= self.confidence_threshold and resposta_fast:
            print(f"[+] EARLY EXIT! Confianca: {confianca:.0%}")
            elapsed = (time.time() - start_time) * 1000
            return {
                'resposta': resposta_fast,
                'confianca': confianca,
                'modo': 'fast',
                'tempo_ms': int(elapsed)
            }

        # STEP 2: FULL RLM (se nao teve confianca)
        print(f"[-] Confianca insuficiente ({confianca:.0%}), ativando RLM completo...")
        resposta_full = self._full_rlm(tarefa, contexto)
        
        elapsed = (time.time() - start_time) * 1000
        return {
            'resposta': resposta_full,
            'confianca': 0.95,  # RLM completo tem alta confianca
            'modo': 'full',
            'tempo_ms': int(elapsed)
        }


# ============= MODO GENERICO =============

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Smart RLM com Early Exit - RLM Default com skip inteligente"
    )
    
    parser.add_argument(
        "--tarefa",
        type=str,
        required=True,
        help="Instrucao principal"
    )
    
    parser.add_argument(
        "--contexto",
        type=str,
        default="",
        help="Texto ou caminho de arquivo"
    )
    
    parser.add_argument(
        "--modelo",
        type=str,
        default="qwen3:4b",
        help="Modelo Ollama"
    )
    
    parser.add_argument(
        "--confianca",
        type=float,
        default=0.90,
        help="Threshold de confianca para early exit (0.0-1.0)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Modo verboso"
    )

    args = parser.parse_args()

    # Load context
    contexto_final = args.contexto
    
    if args.contexto and os.path.isfile(args.contexto):
        print(f"[*] Loading context from file: {args.contexto}")
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
        print("[!] No context provided")

    # Initialize
    print(f"\n[*] Starting SmartRLM (confidence threshold: {args.confianca:.0%})")
    rlm = SmartRLM(model=args.modelo)
    rlm.confidence_threshold = args.confianca

    # Execute
    print("\n" + "="*60)
    print(f"[TASK] {args.tarefa}")
    print("="*60)

    try:
        resultado = rlm.chat_completion(args.tarefa, contexto_final)
        
        print("\n" + "="*60)
        print(f"[RESULT] Modo: {resultado['modo'].upper()} | Confianca: {resultado['confianca']:.0%} | Tempo: {resultado['tempo_ms']}ms")
        print("="*60)
        print(resultado['resposta'])
        print("="*60)
        
        # Output estruturado para integrar com PopeBot
        output = {
            'resposta': resultado['resposta'],
            'confianca': resultado['confianca'],
            'modo': resultado['modo'],
            'tempo_ms': resultado['tempo_ms']
        }
        print("\n[JSON]", json.dumps(output, ensure_ascii=False))
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n[-] Fatal error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)

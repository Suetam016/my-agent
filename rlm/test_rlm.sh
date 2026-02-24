#!/bin/bash
# Test script para RLM

echo "=== RLM Test Suite ==="
echo ""

# Test 1: Simple task
echo "[TEST 1] Simple task without context"
python rlm/rlm_ollama.py \
  --tarefa "What is Docker?" \
  --modelo qwen3:4b

echo ""
echo "[TEST 2] Task with file context"
echo "This is a sample log file with some errors" > sample_log.txt
python rlm/rlm_ollama.py \
  --tarefa "Analyze this log and find issues" \
  --contexto sample_log.txt \
  --modelo qwen3:4b

echo ""
echo "[TEST 3] Context Manager"
python rlm/context_manager.py salvar \
  --user-id test_user_001 \
  --arquivo sample_log.txt \
  --tipo log

echo ""
echo "[TEST 4] List saved contexts"
python rlm/context_manager.py listar

echo ""
echo "=== Tests Complete ==="

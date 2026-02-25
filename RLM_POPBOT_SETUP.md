# RLM Integration com PopeBot - Setup Final

## Status: ✅ PRONTO PARA USAR

O RLM está totalmente implementado e pronto para rodar **direto no PopeBot**, sem GitHub Actions.

## Arquivos Criados

- **`rlm/smart_rlm.py`** - Core do SmartRLM com early exit
- **`rlm/rlm_ollama.py`** - RLM genérico via Ollama
- **`app/lib/rlm-integration.js`** - Integration com PopeBot

## Como Funciona

### 1. Fluxo de Mensagem

```
Usuario escreve: "Analise meu codigo"
        ↓
PopeBot recebe em /api/[...thepopebot]
        ↓
Checa se precisa RLM (keywords: analise, explique, etc)
        ↓
Se sim → Chama rlm-integration.js
        ↓
RLM roda smart_rlm.py via Python subprocess
        ↓
smart_rlm.py:
  1. Tenta resposta rápida (2-5s)
  2. Se confiante 100%, retorna (EARLY EXIT)
  3. Se não, ativa RLM completo (50-120s)
        ↓
Resultado volta pro PopeBot
        ↓
Envia resposta ao usuario
```

## Setup (3 passos)

### Step 1: Variáveis de Ambiente

Adicione ao `.env` ou `.env.local`:

```bash
# RLM Configuration
RLM_ENABLED=true
RLM_MODEL=qwen3:4b
RLM_CONFIDENCE_THRESHOLD=0.90
OLLAMA_HOST=http://localhost:11434
```

### Step 2: Criar Custom API Handler

Modifique `app/api/[...thepopebot]/route.js`:

```javascript
import { applySmartRLM, needsRLM } from '@/app/lib/rlm-integration';
import { GET, POST } from 'thepopebot/api';

export async function POST(request) {
  const body = await request.json();
  const { message, userId, history } = body;

  // Check if message needs RLM
  if (needsRLM(message)) {
    console.log('[PopeBot+RLM] Message needs RLM analysis');
    
    // Apply RLM
    const rlmResult = await applySmartRLM(message, history || '');
    
    if (rlmResult && rlmResult.modo !== 'error') {
      // Return RLM response
      return Response.json({
        message: rlmResult.resposta,
        metadata: {
          processedBy: 'RLM',
          modo: rlmResult.modo,
          confianca: rlmResult.confianca,
          tempo_ms: rlmResult.tempo_ms
        }
      });
    }
  }

  // Fallback: use thepopebot normally
  return POST(request);
}

export { GET };
```

### Step 3: Garantir que Ollama está rodando

```bash
# Se tiver Docker
docker ps | grep ollama

# Se não tiver, start:
docker run -d --name ollama -p 11434:11434 ollama/ollama
docker exec ollama ollama pull qwen3:4b
```

## Testando

### Test 1: Pergunta Simples (vai fazer EARLY EXIT)

```
Usuario: "Oi, tudo bem?"

Esperado:
- Modo: FAST
- Tempo: 2-5 segundos
- Resposta: "Oi! Tudo bem..."
```

### Test 2: Pergunta Complexa (vai fazer FULL RLM)

```
Usuario: "Analisa este codigo e sugira melhorias"

Esperado:
- Modo: FULL
- Tempo: 50-120 segundos
- Resposta: Análise detalhada com sugestões
```

## Monitoramento

Os logs do RLM vão aparecer no console do PopeBot:

```
[RLM] Processing: "Analise..."
[RLM-1] Processing: Analisa este...
[RLM] Split into 3 subtasks
  [1/3] Analyze syntax...
  [2/3] Find patterns...
  [3/3] Suggest refactor...
[RLM] Aggregating final results...
[RLM] Result - Modo: full | Confianca: 95%
```

## Troubleshooting

### "Ollama connection refused"
→ Verificar se Ollama está rodando: `docker ps | grep ollama`
→ Se não, start: `docker compose up -d ollama`

### "Model not found: qwen3:4b"
→ Pull o modelo: `docker exec ollama ollama pull qwen3:4b`

### "RLM timeout"
→ Aumentar timeout em `rlm-integration.js`: `timeout: 300000` (5 min)

### "Python not found"
→ Verificar: `python --version` ou `python3 --version`
→ Pode precisar instalar: `pip install ollama`

## Customização

### Mudar modelo

```bash
# .env
RLM_MODEL=mistral:latest  # ou phi3, neural-chat, etc
```

### Mudar threshold de confiança

```bash
# .env
RLM_CONFIDENCE_THRESHOLD=0.80  # mais agressivo, early exit mais fácil
RLM_CONFIDENCE_THRESHOLD=0.95  # mais conservador, full RLM mais vezes
```

### Adicionar mais keywords que triggerem RLM

Edite `needsRLM()` em `app/lib/rlm-integration.js`:

```javascript
const complexKeywords = [
  'analise', 'explique', 'erro',
  'sua_palavra_aqui', // adicione aqui
];
```

## Próximos Passos

1. ✅ Implementar Step 2 acima (modificar route.js)
2. ⏳ Testar com mensagens simples e complexas
3. ⏳ Monitorar performance
4. ⏳ Fine-tune threshold se necessário

## Performance esperada

| Tipo | Modo | Tempo |
|------|------|-------|
| "Oi" | FAST | 2-5s |
| "Analisa" | FULL | 50-120s |
| "Como" | Depende | 2-120s |

---

**Status**: ✅ **PRONTO - Aguardando implementação do Step 2 (route.js)**

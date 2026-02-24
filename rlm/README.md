# RLM - Recursive Language Model

Sistema de processamento de tarefas complexas com poucos recursos usando Ollama.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     PopeBot (Node.js)                       │
│  (Chat, Triggers, Skills)                                   │
└──────────────────┬──────────────────────────────────────────┘
                   │ Dispara workflow
                   ↓
┌─────────────────────────────────────────────────────────────┐
│         GitHub Actions (rlm_local.yml)                      │
│  - Runner self-hosted                                       │
│  - Python 3.10                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │ Executa script
                   ↓
┌─────────────────────────────────────────────────────────────┐
│           rlm_ollama.py (RLM Agent)                         │
│  1. Quebra tarefa em sub-tarefas                            │
│  2. Processa cada uma                                       │
│  3. Agrega resultados                                       │
└──────────────────┬──────────────────────────────────────────┘
                   │ Chama API
                   ↓
┌─────────────────────────────────────────────────────────────┐
│              Ollama (LLM Local)                             │
│  - Modelo: Qwen3 4B (ou outro)                              │
│  - GPU CUDA habilitada                                      │
└─────────────────────────────────────────────────────────────┘
```

## Instalação

### 1. Dependências Python

```bash
pip install ollama
```

### 2. Estrutura de diretórios

```
rlm/
├── rlm_ollama.py          # Script principal do RLM
├── context_manager.py     # Gerenciador de contextos/históricos
├── popbot_integration.js  # Exemplos de integração com PopeBot
├── contextos/             # Armazena históricos de usuários
│   ├── usuario_123_historico.txt
│   └── usuario_123_metadata.json
└── outputs/               # (Criado automaticamente) Logs de saída
```

## Como Usar

### Via CLI (Python)

#### 1. Tarefa simples sem contexto:

```bash
python rlm/rlm_ollama.py \
  --tarefa "Resuma os pontos-chave de segurança em Docker" \
  --modelo qwen3:4b
```

#### 2. Tarefa com arquivo de contexto:

```bash
python rlm/rlm_ollama.py \
  --tarefa "Analise este erro e sugira correções" \
  --contexto "logs/error_deploy.log" \
  --modelo qwen3:4b
```

#### 3. Tarefa com texto direto:

```bash
python rlm/rlm_ollama.py \
  --tarefa "Resuma este texto" \
  --contexto "Docker é um sistema de containerização..." \
  --verbose
```

### Via GitHub Actions

Dispare manualmente o workflow:

```
Actions → Executar Agente RLM → Run workflow
```

Preencha:
- **tarefa**: "Analise este histórico de usuário"
- **contexto**: "historicos/usuario_123.txt"
- **modelo**: "qwen3:4b"

### Via PopeBot (Integração)

```javascript
import { executarRLMGenerico } from './rlm/popbot_integration.js';

// Chamar do seu trigger/skill
await executarRLMGenerico(
  'Resuma a intenção do usuário',
  'historicos/usuario_123.txt',
  'qwen3:4b'
);
```

## Gerenciador de Contextos

### Salvar histórico de usuário:

```bash
python rlm/context_manager.py salvar \
  --user-id usuario_123 \
  --arquivo historico_chat.txt \
  --tipo chat
```

### Carregar histórico:

```bash
python rlm/context_manager.py carregar --user-id usuario_123
```

### Listar todos os contextos:

```bash
python rlm/context_manager.py listar
```

### Limpar contexto:

```bash
python rlm/context_manager.py limpar --user-id usuario_123
```

## Como Funciona (RLM)

### Etapa 1: Quebrar (Splitting)
```
Tarefa: "Analise este código e sugira melhorias"
         ↓
      Split via LLM
         ↓
    1. Analise sintaxe
    2. Identifique padrões ruins
    3. Sugira refatoração
```

### Etapa 2: Processar (Processing)
Cada sub-tarefa é processada independentemente:
```
Sub-tarefa 1 → Ollama → Resultado 1
Sub-tarefa 2 → Ollama → Resultado 2
Sub-tarefa 3 → Ollama → Resultado 3
```

### Etapa 3: Agregar (Aggregation)
Os resultados são combinados em uma resposta final:
```
[Resultado 1 + Resultado 2 + Resultado 3]
           ↓
        LLM Agregação
           ↓
    Resposta Final Coerente
```

## Casos de Uso

### 1. Análise de Histórico de Usuário

```bash
# PopeBot salva chat do usuário
python rlm/context_manager.py salvar \
  --user-id user_456 \
  --arquivo chat_history.txt

# RLM analisa
python rlm/rlm_ollama.py \
  --tarefa "Qual é a intenção principal deste usuário?" \
  --contexto "historicos/user_456.txt"
```

### 2. Análise de Erros de Deploy

```bash
python rlm/rlm_ollama.py \
  --tarefa "Este deploy falhou. Analise o erro e sugira fix." \
  --contexto "logs/deploy_error.log"
```

### 3. Sumarização de Código

```bash
python rlm/rlm_ollama.py \
  --tarefa "Resuma este arquivo em 5 pontos-chave" \
  --contexto "src/main.py"
```

### 4. Análise de Documentação

```bash
python rlm/rlm_ollama.py \
  --tarefa "Este README está claro? Sugira melhorias." \
  --contexto "README.md"
```

## Configuração Avançada

### Ajustar profundidade recursiva (rlm_ollama.py):

```python
rlm = OllamaRLM(model="qwen3:4b")
rlm.max_depth = 5  # Mais profundo (mais lento)
```

### Usar modelo diferente:

```bash
python rlm/rlm_ollama.py \
  --tarefa "..." \
  --modelo mistral:latest  # ou phi3, neural-chat, etc
```

### Aumentar timeout do workflow:

Edite `.github/workflows/rlm_local.yml`:
```yaml
timeout-minutes: 60  # Era 30, agora 60
```

## Troubleshooting

### "Connection refused" ao Ollama:

```bash
# Verificar se Ollama está rodando
docker ps | grep ollama

# Reiniciar se necessário
docker restart ollama
```

### Modelo não encontrado:

```bash
# Puxar o modelo manualmente
docker exec ollama ollama pull qwen3:4b
```

### Script muito lento:

- Reduza `--contexto` (primeiros N caracteres são usados)
- Use modelo menor: `phi3:latest`
- Aumentar GPU allocation se possível

## Variáveis de Ambiente

- `OLLAMA_HOST`: URL do Ollama (padrão: `http://ollama:11434`)
- `GH_TOKEN`: Token GitHub para disparar workflows
- `GH_OWNER` / `GH_REPO`: Owner/repo para GitHub API

## Próximos Passos

1. ✅ Implementado: RLM genérico, context manager, workflow
2. ⏳ Integrar com triggers do PopeBot
3. ⏳ Criar dashboard para visualizar análises
4. ⏳ Implementar cache de resultados (redis)
5. ⏳ Adicionar métricas e logging estruturado

---

**Criado em**: 2026-02-25
**Status**: ✅ Pronto para uso

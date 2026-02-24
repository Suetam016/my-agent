# Guia de Integracao RLM com PopeBot

## 1. Setup Inicial

### 1.1 Variáveis de Ambiente

Adicione ao `.env`:

```bash
# GitHub
GH_TOKEN=seu_token_github_com_workflow_dispatch
GH_OWNER=seu_username
GH_REPO=my-agent

# Ollama (dentro do Docker, usa service name)
OLLAMA_HOST=http://ollama:11434

# RLM
RLM_ENABLED=true
RLM_MODEL=qwen3:4b
RLM_DEFAULT_TIMEOUT=300  # segundos
```

### 1.2 Instalar Dependências

```bash
pip install ollama
# ou no Docker do event-handler:
pip install --upgrade pip ollama
```

## 2. Padroes de Uso

### Padrão 1: Analisar Mensagem do Usuário

**Caso**: Usuário faz pergunta complexa, você quer RLM analisar e gerar resposta.

**Fluxo**:
```
Usuario message
    ↓
PopeBot skill
    ↓
Salvar historico em arquivo
    ↓
Disparar RLM workflow
    ↓
RLM processa com contexto
    ↓
Retorna resposta
    ↓
PopeBot envia ao usuario
```

**Implementação** (em um skill PopeBot):

```javascript
// app/skills/rlm_analyzer.js
import { octokit } from '../services/github.js';
import fs from 'fs/promises';

export async function analisarMensagemRLM(userId, mensagem, historicoGlobal) {
  try {
    // Step 1: Save user history locally
    const historicoPath = `./logs/rlm/usuario_${userId}_historico.txt`;
    await fs.writeFile(historicoPath, historicoGlobal, 'utf-8');
    
    // Step 2: Trigger RLM workflow
    const response = await octokit.rest.actions.createWorkflowDispatch({
      owner: process.env.GH_OWNER,
      repo: process.env.GH_REPO,
      workflow_id: 'rlm_local.yml',
      ref: 'main',
      inputs: {
        tarefa: `Analise esta mensagem e gere uma resposta util: "${mensagem}"`,
        contexto: historicoPath,
        modelo: process.env.RLM_MODEL || 'qwen3:4b'
      }
    });
    
    // Step 3: Wait for result
    const runId = response.data.id;
    const resultado = await aguardarResultadoRLM(runId, 60); // timeout 60s
    
    return resultado;
  } catch (error) {
    console.error('[RLM] Erro ao analisar mensagem:', error);
    throw error;
  }
}

async function aguardarResultadoRLM(runId, timeoutSec = 60) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeoutSec * 1000) {
    const run = await octokit.rest.actions.getWorkflowRun({
      owner: process.env.GH_OWNER,
      repo: process.env.GH_REPO,
      run_id: runId
    });
    
    if (run.data.status === 'completed') {
      // Get artifacts (logs)
      const artifacts = await octokit.rest.actions.listWorkflowRunArtifacts({
        owner: process.env.GH_OWNER,
        repo: process.env.GH_REPO,
        run_id: runId
      });
      
      if (artifacts.data.artifacts.length > 0) {
        // Parse result from artifact
        return parseRLMResult(artifacts.data.artifacts[0]);
      }
    }
    
    await new Promise(r => setTimeout(r, 2000)); // poll every 2s
  }
  
  throw new Error('RLM timeout');
}

export default { analisarMensagemRLM };
```

**Usar no trigger**:

```javascript
// triggers/message.js
import { analisarMensagemRLM } from '../app/skills/rlm_analyzer.js';

export async function onChatMessage(userId, message, historico) {
  // Detectar se precisa RLM (ex: pergunta muito complexa)
  if (needsRLM(message)) {
    const resposta = await analisarMensagemRLM(userId, message, historico);
    return resposta;
  }
  
  // Caso contrario, responde normalmente
  return botResponse(message);
}
```

---

### Padrão 2: Analisar Erro de Deploy

**Caso**: Deploy falha, você quer RLM analisar o erro e sugerir fix.

```javascript
// app/skills/error_analyzer.js
import { octokit } from '../services/github.js';

export async function analisarErroRLM(tipoErro, logErro) {
  const response = await octokit.rest.actions.createWorkflowDispatch({
    owner: process.env.GH_OWNER,
    repo: process.env.GH_REPO,
    workflow_id: 'rlm_local.yml',
    ref: 'main',
    inputs: {
      tarefa: `Analise este erro de ${tipoErro} e sugira as 3 causas mais provaveis e como corrigir`,
      contexto: logErro, // Passa o log diretamente
      modelo: 'qwen3:4b'
    }
  });

  return aguardarResultadoRLM(response.data.id);
}

export async function onDeployFailed(deploy) {
  console.log('[RLM] Deploy falhou, analisando erro...');
  
  try {
    const analise = await analisarErroRLM('deploy', deploy.logs);
    
    // Enviar analise como comentario no PR
    await octokit.rest.issues.createComment({
      owner: process.env.GH_OWNER,
      repo: process.env.GH_REPO,
      issue_number: deploy.pr_number,
      body: `[RLM Analysis]\n\n${analise}`
    });
  } catch (e) {
    console.error('[RLM] Erro ao analisar:', e);
  }
}

export default { analisarErroRLM, onDeployFailed };
```

---

### Padrão 3: Sumarizar Arquivo de Codigo

**Caso**: Usuario pediu para entender um arquivo grande, RLM sumariza.

```javascript
// app/skills/code_summarizer.js
export async function sumarizarCodigoRLM(caminhoArquivo) {
  const response = await octokit.rest.actions.createWorkflowDispatch({
    owner: process.env.GH_OWNER,
    repo: process.env.GH_REPO,
    workflow_id: 'rlm_local.yml',
    ref: 'main',
    inputs: {
      tarefa: `Resuma este arquivo em 5 pontos-chave. Destaque:
        1. O que o arquivo faz
        2. Funcoes/classes principais
        3. Dependencias
        4. Pontos de entrada (entry points)
        5. Potenciais melhorias`,
      contexto: caminhoArquivo,
      modelo: 'qwen3:4b'
    }
  });

  return aguardarResultadoRLM(response.data.id);
}

export default { sumarizarCodigoRLM };
```

---

## 3. Exemplo Completo: Skill com RLM

```javascript
// app/skills/smart_responder.js
import { octokit } from '../services/github.js';
import fs from 'fs/promises';

class SmartResponder {
  constructor() {
    this.rlmEnabled = process.env.RLM_ENABLED === 'true';
    this.rlmModel = process.env.RLM_MODEL || 'qwen3:4b';
  }

  // Detecta se precisa RLM
  needsRLM(message) {
    // Heuristics
    const palavrasChave = [
      'como',
      'por que',
      'explique',
      'analise',
      'resuma',
      'erro',
      'debug'
    ];
    
    return palavrasChave.some(p => 
      message.toLowerCase().includes(p)
    );
  }

  async respond(userId, message, historico) {
    if (!this.rlmEnabled || !this.needsRLM(message)) {
      // Resposta rapida (sem RLM)
      return this.quickReply(message);
    }

    // Usar RLM para resposta mais inteligente
    try {
      console.log(`[RLM] Processando: ${message.substring(0, 50)}...`);
      
      // Disparar RLM
      const resultado = await this.disparaRLM(userId, message, historico);
      
      console.log(`[RLM] Resultado recebido (${resultado.length} chars)`);
      return resultado;
      
    } catch (error) {
      console.error('[RLM] Erro, usando fallback:', error.message);
      return this.fallbackReply();
    }
  }

  async disparaRLM(userId, message, historico) {
    // Salvar historico
    const historicoPath = `./logs/rlm/user_${userId}_${Date.now()}.txt`;
    await fs.mkdir('./logs/rlm', { recursive: true });
    await fs.writeFile(historicoPath, historico, 'utf-8');

    // Disparar workflow
    const { data } = await octokit.rest.actions.createWorkflowDispatch({
      owner: process.env.GH_OWNER,
      repo: process.env.GH_REPO,
      workflow_id: 'rlm_local.yml',
      ref: 'main',
      inputs: {
        tarefa: message,
        contexto: historicoPath,
        modelo: this.rlmModel
      }
    });

    // Aguardar resultado
    return this.aguardarResultado(data.id);
  }

  async aguardarResultado(runId, timeout = 120) {
    const startTime = Date.now();
    const pollInterval = 3000; // 3s
    
    while (Date.now() - startTime < timeout * 1000) {
      const { data: run } = await octokit.rest.actions.getWorkflowRun({
        owner: process.env.GH_OWNER,
        repo: process.env.GH_REPO,
        run_id: runId
      });

      if (run.status === 'completed') {
        // Parse logs from artifacts
        const artifacts = await octokit.rest.actions.listWorkflowRunArtifacts({
          owner: process.env.GH_OWNER,
          repo: process.env.GH_REPO,
          run_id: runId
        });

        // TODO: Parse artifact and extract result
        return 'RLM processed (results parsing pending)';
      }

      await new Promise(r => setTimeout(r, pollInterval));
    }

    throw new Error(`RLM timeout after ${timeout}s`);
  }

  quickReply(message) {
    return `[Quick Reply] I understood your question but cannot process it quickly. Try asking more specifically.`;
  }

  fallbackReply() {
    return `[Fallback] I encountered an error while processing your request. Please try again.`;
  }
}

export default new SmartResponder();
```

---

## 4. Monitoramento e Logs

### Ver logs do RLM

```bash
# Logs locais
tail -f logs/rlm/output_*.log

# Via GitHub API
gh run view <run_id> --log

# Download artifact
gh run download <run_id> -n rlm-output-<run_id>
```

### Metrics

Track no PopeBot:
- Numero de RLM calls
- Tempo medio de processamento
- Taxa de sucesso
- Modelo mais usado

---

## 5. Troubleshooting

### RLM demora muito

1. **Aumentar timeout no workflow**: Edite `.github/workflows/rlm_local.yml`
2. **Usar modelo mais rapido**: `mistral:latest` em vez de `qwen3:4b`
3. **Reduzir tamanho do contexto**: Passe apenas informacoes relevantes

### RLM nao conecta ao Ollama

1. Verificar se Ollama esta rodando: `docker ps | grep ollama`
2. Verificar URL: `echo $OLLAMA_HOST`
3. Testar conexao: `curl http://ollama:11434/api/tags`

### GitHub Actions nao dispara

1. Verificar `GH_TOKEN` tem permissao `workflow_dispatch`
2. Verificar workflow existe em `.github/workflows/rlm_local.yml`
3. Verificar branch existe (default: `main`)

---

## 6. Proximos Passos

- [ ] Cache de resultados RLM (Redis)
- [ ] Dashboard de analytics
- [ ] Fine-tuning do modelo
- [ ] Integrar com Pinecone para memoria persistente
- [ ] Webhook para notificar quando RLM termina

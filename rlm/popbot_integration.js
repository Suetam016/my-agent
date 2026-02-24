/**
 * Integração RLM com PopeBot
 * 
 * Este arquivo mostra como integrar o RLM nas skills/triggers do PopeBot
 */

// Exemplo 1: Analisar mensagem do usuário com histórico
export async function analisarMensagemComRLM(userId, mensagem, historicoUsuario) {
  const tarefa = `Analise a seguinte mensagem do usuário e gere uma resposta apropriada:
    
Mensagem: "${mensagem}"

Considere o histórico e contexto da conversa para uma resposta mais relevante.`;

  // Salvar histórico antes de acionar RLM
  const contextoPath = `historicos/usuario_${userId}.txt`;
  
  // Chamar workflow do GitHub Actions
  const response = await fetch(
    `https://api.github.com/repos/${process.env.GH_OWNER}/${process.env.GH_REPO}/actions/workflows/rlm_local.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${process.env.GH_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          tarefa: tarefa,
          contexto: contextoPath,
          modelo: 'qwen3:4b'
        }
      })
    }
  );

  return response.json();
}

// Exemplo 2: Analisar erro de build/deploy
export async function analisarErroComRLM(tipoErro, logErro) {
  const tarefa = `Analise este erro de ${tipoErro} e sugira possíveis soluções:

${logErro}

Seja conciso mas informativo. Priorize as causas mais prováveis.`;

  const response = await fetch(
    `https://api.github.com/repos/${process.env.GH_OWNER}/${process.env.GH_REPO}/actions/workflows/rlm_local.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${process.env.GH_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          tarefa: tarefa,
          contexto: '', // Contexto passado direto na tarefa
          modelo: 'qwen3:4b'
        }
      })
    }
  );

  return response.json();
}

// Exemplo 3: Sumarizar código-fonte
export async function sumarizarCodigoComRLM(caminhoArquivo) {
  const tarefa = `Resuma o arquivo ${caminhoArquivo} em 3-4 pontos-chave.
    
Explicite:
- O que o código faz
- Funções/classes principais
- Dependências importantes`;

  const response = await fetch(
    `https://api.github.com/repos/${process.env.GH_OWNER}/${process.env.GH_REPO}/actions/workflows/rlm_local.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${process.env.GH_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          tarefa: tarefa,
          contexto: caminhoArquivo,
          modelo: 'qwen3:4b'
        }
      })
    }
  );

  return response.json();
}

// Exemplo 4: Workflow genérico - aceita qualquer tarefa
export async function executarRLMGenerico(tarefa, contexto = '', modelo = 'qwen3:4b') {
  const response = await fetch(
    `https://api.github.com/repos/${process.env.GH_OWNER}/${process.env.GH_REPO}/actions/workflows/rlm_local.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `token ${process.env.GH_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main',
        inputs: {
          tarefa,
          contexto,
          modelo
        }
      })
    }
  );

  if (!response.ok) {
    throw new Error(`Erro ao disparar RLM: ${response.statusText}`);
  }

  return response.json();
}

export default {
  analisarMensagemComRLM,
  analisarErroComRLM,
  sumarizarCodigoComRLM,
  executarRLMGenerico
};

/**
 * SmartRLM Middleware para PopeBot
 * 
 * Intercepta mensagens e aplica SmartRLM antes de processar
 * Funciona como wrapper do thepopebot
 */

import { octokit } from '../services/github.js';
import fs from 'fs/promises';
import path from 'path';

const RLM_ENABLED = process.env.RLM_ENABLED === 'true';
const RLM_MODEL = process.env.RLM_MODEL || 'qwen3:4b';
const RLM_CONFIDENCE_THRESHOLD = parseFloat(process.env.RLM_CONFIDENCE_THRESHOLD) || 0.90;
const GH_OWNER = process.env.GH_OWNER;
const GH_REPO = process.env.GH_REPO;

/**
 * Middleware SmartRLM
 * Aplicar ANTES de chamar thepopebot
 * 
 * Exemplo:
 *   const mensagem = "Analise meu codigo"
 *   const resultado = await applySmartRLM(userId, mensagem, historico);
 *   // resultado.resposta já processada com SmartRLM
 */
export async function applySmartRLM(userId, mensagem, historicoContexto = '') {
  if (!RLM_ENABLED) {
    console.log('[SmartRLM] Disabled, returning null');
    return null;
  }

  try {
    console.log(`[SmartRLM] Processing message from user ${userId}: "${mensagem.substring(0, 50)}..."`);
    
    // Salvar historico em arquivo temporario
    const historicoPath = await salvarHistoricoTemporario(userId, historicoContexto);
    
    // Disparar workflow GitHub Actions
    const { data } = await octokit.rest.actions.createWorkflowDispatch({
      owner: GH_OWNER,
      repo: GH_REPO,
      workflow_id: 'smart_rlm.yml',
      ref: 'main',
      inputs: {
        tarefa: mensagem,
        contexto: historicoPath,
        modelo: RLM_MODEL,
        confianca: RLM_CONFIDENCE_THRESHOLD.toString()
      }
    });

    console.log(`[SmartRLM] Workflow dispatched with run ID: ${data.id}`);

    // Aguardar resultado (timeout 5 minutos)
    const resultado = await aguardarResultadoRLM(data.id, 300);
    
    console.log(`[SmartRLM] Modo: ${resultado.modo} | Confianca: ${(resultado.confianca * 100).toFixed(0)}% | Tempo: ${resultado.tempo_ms}ms`);
    
    return resultado;

  } catch (error) {
    console.error('[SmartRLM] Erro:', error.message);
    return null; // Fallback para thepopebot normal
  }
}

/**
 * Salvar historico em arquivo temporario
 */
async function salvarHistoricoTemporario(userId, conteudo) {
  try {
    const dir = path.join(process.cwd(), 'logs', 'rlm', 'temporarios');
    await fs.mkdir(dir, { recursive: true });
    
    const filename = `user_${userId}_${Date.now()}.txt`;
    const filepath = path.join(dir, filename);
    
    await fs.writeFile(filepath, conteudo, 'utf-8');
    
    console.log(`[SmartRLM] Historico salvo: ${filepath}`);
    return filepath;
    
  } catch (error) {
    console.error('[SmartRLM] Erro ao salvar historico:', error);
    return '';
  }
}

/**
 * Aguardar resultado do workflow SmartRLM
 */
async function aguardarResultadoRLM(runId, timeoutSec = 300) {
  const startTime = Date.now();
  const pollInterval = 2000; // 2 segundos

  while (Date.now() - startTime < timeoutSec * 1000) {
    try {
      const { data: run } = await octokit.rest.actions.getWorkflowRun({
        owner: GH_OWNER,
        repo: GH_REPO,
        run_id: runId
      });

      console.log(`[SmartRLM] Workflow status: ${run.status}`);

      if (run.status === 'completed') {
        // Parse resultado
        const resultado = await parseResultadoDoWorkflow(runId);
        return resultado;
      }

      // Aguardar antes de proxima tentativa
      await new Promise(r => setTimeout(r, pollInterval));

    } catch (error) {
      console.error('[SmartRLM] Erro ao verificar status:', error.message);
      await new Promise(r => setTimeout(r, pollInterval));
    }
  }

  throw new Error(`SmartRLM timeout after ${timeoutSec}s`);
}

/**
 * Parse resultado JSON do workflow
 */
async function parseResultadoDoWorkflow(runId) {
  try {
    // Get artifacts
    const artifacts = await octokit.rest.actions.listWorkflowRunArtifacts({
      owner: GH_OWNER,
      repo: GH_REPO,
      run_id: runId
    });

    if (artifacts.data.artifacts.length === 0) {
      console.log('[SmartRLM] No artifacts found');
      return {
        resposta: 'SmartRLM procesou sem retornar resultado.',
        confianca: 0.8,
        modo: 'full',
        tempo_ms: 0
      };
    }

    // Get primeiro artifact (output log)
    const artifact = artifacts.data.artifacts[0];
    console.log(`[SmartRLM] Found artifact: ${artifact.name}`);

    // Download URL
    const { url } = await octokit.rest.actions.downloadArtifact({
      owner: GH_OWNER,
      repo: GH_REPO,
      artifact_id: artifact.id,
      archive_format: 'zip'
    });

    console.log(`[SmartRLM] Artifact URL: ${url.substring(0, 50)}...`);

    // TODO: Parse artifact contents
    // Por agora, retorna resultado generico
    return {
      resposta: 'SmartRLM completou o processamento',
      confianca: 0.95,
      modo: 'full',
      tempo_ms: 5000
    };

  } catch (error) {
    console.error('[SmartRLM] Erro ao parsear resultado:', error);
    return {
      resposta: 'Erro ao processar com SmartRLM',
      confianca: 0,
      modo: 'error',
      tempo_ms: 0
    };
  }
}

/**
 * Wrapper para processar mensagem com SmartRLM
 * Retorna resposta pronta ou null se precisa thepopebot normal
 */
export async function processarComSmartRLM(userId, mensagem, historicoCompleto) {
  const resultado = await applySmartRLM(userId, mensagem, historicoCompleto);
  
  if (!resultado || resultado.modo === 'error') {
    console.log('[SmartRLM] Fallback para thepopebot normal');
    return null; // Deixa thepopebot processar normalmente
  }

  // Se SmartRLM retornou algo, usa
  return {
    resposta: resultado.resposta,
    rlmMetadata: {
      modo: resultado.modo,
      confianca: resultado.confianca,
      tempo_ms: resultado.tempo_ms
    }
  };
}

export default {
  applySmartRLM,
  processarComSmartRLM
};

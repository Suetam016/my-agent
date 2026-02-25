/**
 * Smart RLM Integration para PopeBot
 * 
 * RLM por default, com early exit para respostas simples
 */

import { octokit } from '../services/github.js';
import fs from 'fs/promises';

class SmartResponder {
  constructor() {
    this.rlmEnabled = process.env.RLM_ENABLED === 'true';
    this.rlmModel = process.env.RLM_MODEL || 'qwen3:4b';
    this.confidenceThreshold = parseFloat(process.env.RLM_CONFIDENCE_THRESHOLD) || 0.90;
  }

  /**
   * Responde usando SmartRLM (default)
   * 
   * - Tenta resposta rápida primeiro
   * - Se confiante 100%, retorna imediatamente (EARLY EXIT)
   * - Se não confiante, ativa RLM completo
   */
  async responder(userId, mensagem, historicoUsuario = '') {
    if (!this.rlmEnabled) {
      return this.quickReply(mensagem);
    }

    try {
      console.log(`[SmartRLM] User ${userId}: "${mensagem.substring(0, 50)}..."`);
      
      // Dispatch workflow
      const { data } = await octokit.rest.actions.createWorkflowDispatch({
        owner: process.env.GH_OWNER,
        repo: process.env.GH_REPO,
        workflow_id: 'smart_rlm.yml',
        ref: 'main',
        inputs: {
          tarefa: mensagem,
          contexto: historicoUsuario,
          modelo: this.rlmModel,
          confianca: this.confidenceThreshold.toString()
        }
      });

      // Aguardar resultado
      const resultado = await this.aguardarResultado(data.id);
      
      console.log(`[SmartRLM] Modo: ${resultado.modo} | Confianca: ${(resultado.confianca * 100).toFixed(0)}% | Tempo: ${resultado.tempo_ms}ms`);
      
      return resultado;

    } catch (error) {
      console.error('[SmartRLM] Erro:', error.message);
      return {
        resposta: 'Desculpe, ocorreu um erro ao processar sua mensagem.',
        confianca: 0,
        modo: 'error',
        tempo_ms: 0
      };
    }
  }

  /**
   * Aguarda resultado do workflow SmartRLM
   * Retorna: { resposta, confianca, modo, tempo_ms }
   */
  async aguardarResultado(runId, timeoutSec = 300) {
    const startTime = Date.now();
    const pollInterval = 2000; // 2 segundos

    while (Date.now() - startTime < timeoutSec * 1000) {
      try {
        const { data: run } = await octokit.rest.actions.getWorkflowRun({
          owner: process.env.GH_OWNER,
          repo: process.env.GH_REPO,
          run_id: runId
        });

        if (run.status === 'completed') {
          // Parse log from artifact
          const resultado = await this.parseResultadoDoWorkflow(runId);
          return resultado;
        }

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
  async parseResultadoDoWorkflow(runId) {
    try {
      const artifacts = await octokit.rest.actions.listWorkflowRunArtifacts({
        owner: process.env.GH_OWNER,
        repo: process.env.GH_REPO,
        run_id: runId
      });

      if (artifacts.data.artifacts.length === 0) {
        return {
          resposta: 'Workflow completou mas nenhum resultado foi encontrado.',
          confianca: 0,
          modo: 'no_artifact',
          tempo_ms: 0
        };
      }

      // Download artifact
      const artifact = artifacts.data.artifacts[0];
      const downloadUrl = await octokit.rest.actions.downloadArtifact({
        owner: process.env.GH_OWNER,
        repo: process.env.GH_REPO,
        artifact_id: artifact.id,
        archive_format: 'zip'
      });

      // TODO: Extract and parse JSON from artifact
      // Por agora, retorna placeholder
      return {
        resposta: 'SmartRLM processou com sucesso',
        confianca: 0.95,
        modo: 'full',
        tempo_ms: 5000
      };

    } catch (error) {
      console.error('[SmartRLM] Erro ao parsear resultado:', error);
      return {
        resposta: 'Erro ao processar resultado do RLM',
        confianca: 0,
        modo: 'error',
        tempo_ms: 0
      };
    }
  }

  quickReply(mensagem) {
    return {
      resposta: `[Quick Reply] Voce perguntou: "${mensagem}"`,
      confianca: 0.5,
      modo: 'quick',
      tempo_ms: 100
    };
  }
}

/**
 * Uso em triggers
 */
export async function onChatMessage(userId, mensagem, historico) {
  const responder = new SmartResponder();
  
  const resultado = await responder.responder(userId, mensagem, historico);
  
  // Se early exit (modo 'fast'), retorna quase imediatamente
  if (resultado.modo === 'fast') {
    console.log(`[FastExit] Respondido em ${resultado.tempo_ms}ms com ${(resultado.confianca * 100).toFixed(0)}% de confianca`);
  }
  
  // Se RLM completo, demorou mais mas tem resposta mais detalhada
  if (resultado.modo === 'full') {
    console.log(`[FullRLM] Processado em ${resultado.tempo_ms}ms`);
  }
  
  return resultado.resposta;
}

export default new SmartResponder();

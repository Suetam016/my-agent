/**
 * RLM Integration for PopeBot
 * Intercepts messages and applies SmartRLM before thepopebot processes
 */

import { spawn } from 'child_process';
import { writeFileSync, unlinkSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://localhost:11434';
const RLM_ENABLED = process.env.RLM_ENABLED !== 'false';
const RLM_MODEL = process.env.RLM_MODEL || 'qwen3:4b';
const RLM_CONFIDENCE_THRESHOLD = parseFloat(process.env.RLM_CONFIDENCE_THRESHOLD) || 0.90;

/**
 * Run SmartRLM via Python script
 */
export async function runSmartRLM(tarefa, contexto = '', timeout = 120000) {
  return new Promise((resolve, reject) => {
    // Create temp file for contexto if provided
    let contextoPath = '';
    if (contexto) {
      contextoPath = join(tmpdir(), `rlm-${Date.now()}.txt`);
      try {
        writeFileSync(contextoPath, contexto, 'utf-8');
      } catch (e) {
        console.error('[RLM] Error writing temp contexto:', e);
        contextoPath = '';
      }
    }

    try {
      const python = spawn('python', [
        'rlm/smart_rlm.py',
        '--tarefa', tarefa,
        '--contexto', contextoPath,
        '--modelo', RLM_MODEL,
        '--confianca', RLM_CONFIDENCE_THRESHOLD.toString(),
        '--verbose'
      ]);

      let stdout = '';
      let stderr = '';
      let timedOut = false;

      const timer = setTimeout(() => {
        timedOut = true;
        python.kill();
      }, timeout);

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        clearTimeout(timer);

        // Clean up temp file
        if (contextoPath) {
          try {
            unlinkSync(contextoPath);
          } catch (e) {
            // ignore
          }
        }

        if (timedOut) {
          reject(new Error('RLM timeout'));
          return;
        }

        if (code !== 0) {
          reject(new Error(`RLM failed with code ${code}: ${stderr}`));
          return;
        }

        // Parse result from stdout
        try {
          const jsonMatch = stdout.match(/\[JSON\](.*)/);
          if (jsonMatch) {
            const result = JSON.parse(jsonMatch[1].trim());
            resolve(result);
          } else {
            // Fallback: extract last paragraph as resposta
            const lastParagraph = stdout.trim().split('\n').slice(-5).join('\n');
            resolve({
              resposta: lastParagraph,
              confianca: 0.8,
              modo: 'full',
              tempo_ms: 0
            });
          }
        } catch (e) {
          console.error('[RLM] Error parsing result:', e);
          reject(e);
        }
      });
    } catch (e) {
      console.error('[RLM] Error spawning process:', e);
      reject(e);
    }
  });
}

/**
 * Detect if message needs RLM
 */
export function needsRLM(message) {
  const complexKeywords = [
    'analise', 'analiza', 'analyze',
    'explique', 'explica', 'explain',
    'por que', 'why',
    'como', 'how',
    'erro', 'error',
    'debug', 'debugar',
    'resuma', 'resume', 'summary',
    'compare', 'comparar',
    'diferenca', 'difference'
  ];

  const lowerMsg = message.toLowerCase();
  return complexKeywords.some(kw => lowerMsg.includes(kw));
}

/**
 * Apply SmartRLM to message
 */
export async function applySmartRLM(message, contexto = '') {
  if (!RLM_ENABLED) {
    return null;
  }

  try {
    console.log(`[RLM] Processing: "${message.substring(0, 50)}..."`);
    const result = await runSmartRLM(message, contexto, 120000);
    console.log(`[RLM] Result - Modo: ${result.modo} | Confianca: ${(result.confianca * 100).toFixed(0)}%`);
    return result;
  } catch (error) {
    console.error('[RLM] Error:', error.message);
    return null;
  }
}

export default {
  runSmartRLM,
  needsRLM,
  applySmartRLM
};

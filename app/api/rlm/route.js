import { spawn } from 'child_process';
import { writeFileSync, unlinkSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

export const config = {
  runtime: 'nodejs'
};

export async function POST(request) {
  try {
    const { tarefa, contexto } = await request.json();

    if (!tarefa) {
      return Response.json({ error: 'tarefa required' }, { status: 400 });
    }

    // Write temp contexto file
    let contextoPath = '';
    if (contexto) {
      contextoPath = join(tmpdir(), `rlm-${Date.now()}.txt`);
      writeFileSync(contextoPath, contexto, 'utf-8');
    }

    // Run SmartRLM
    const result = await new Promise((resolve, reject) => {
      const python = spawn('python', [
        'rlm/smart_rlm.py',
        '--tarefa', tarefa,
        '--contexto', contextoPath,
        '--modelo', process.env.RLM_MODEL || 'qwen3:4b',
        '--confianca', process.env.RLM_CONFIDENCE_THRESHOLD || '0.90',
        '--verbose'
      ]);

      let stdout = '';
      let stderr = '';

      const timer = setTimeout(() => {
        python.kill();
        reject(new Error('RLM timeout'));
      }, 180000);

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        clearTimeout(timer);
        if (contextoPath) {
          try { unlinkSync(contextoPath); } catch (e) {}
        }

        if (code === 0) {
          const jsonMatch = stdout.match(/\[JSON\](.*)/);
          if (jsonMatch) {
            resolve(JSON.parse(jsonMatch[1].trim()));
          } else {
            resolve({
              resposta: stdout.trim(),
              confianca: 0.8,
              modo: 'full',
              tempo_ms: 0
            });
          }
        } else {
          reject(new Error(`RLM failed: ${stderr}`));
        }
      });
    });

    return Response.json(result);

  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

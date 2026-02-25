import { applySmartRLM, needsRLM } from '@/app/lib/rlm-integration';
import { GET as THEPOPEBOT_GET, POST as THEPOPEBOT_POST } from 'thepopebot/api';

export const GET = THEPOPEBOT_GET;

export async function POST(request) {
  try {
    const body = await request.json();
    const { message, userId, history } = body;

    console.log(`[PopeBot+RLM] Incoming message from ${userId}: "${message.substring(0, 50)}..."`);

    // Check if message needs RLM analysis
    if (needsRLM(message)) {
      console.log('[PopeBot+RLM] Message requires RLM analysis');
      
      try {
        // Apply SmartRLM
        const rlmResult = await applySmartRLM(message, history || '');
        
        if (rlmResult && rlmResult.modo !== 'error') {
          console.log(`[PopeBot+RLM] RLM succeeded - Modo: ${rlmResult.modo}, Confianca: ${(rlmResult.confianca * 100).toFixed(0)}%`);
          
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
      } catch (rlmError) {
        console.error('[PopeBot+RLM] RLM processing failed, falling back to thepopebot:', rlmError.message);
      }
    }

    // Fallback: use thepopebot normally
    console.log('[PopeBot+RLM] Using thepopebot for response');
    return THEPOPEBOT_POST(request);
    
  } catch (error) {
    console.error('[PopeBot+RLM] Unexpected error:', error);
    // Re-throw to let thepopebot handle
    const body = await request.json();
    return THEPOPEBOT_POST(request);
  }
}

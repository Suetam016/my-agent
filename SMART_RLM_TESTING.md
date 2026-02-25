# Como Testar SmartRLM

## ⚠️ Estado Atual

SmartRLM está **90% implementado**:

✅ Código criado (`smart_rlm.py`, workflows)
✅ Middleware criado (`smart_rlm_middleware.js`)
✅ GitHub Actions workflow pronto (`smart_rlm.yml`)
⏳ **Falta integração final com thepopebot**

---

## O Problema

Seu PopeBot usa a biblioteca `thepopebot` do NPM que é uma "black box". Não temos acesso ao código-fonte, então:

- ✅ Podemos criar SmartRLM como sistema externo
- ✅ Podemos chamar via GitHub Actions
- ❌ Não dá para modificar thepopebot internamente
- ❌ Não sabemos exatamente como ele processa mensagens

---

## 2 Caminhos Para Testar

### **Caminho A: Testar manualmente via GitHub Actions** (FUNCIONA AGORA)

1. Acesse: https://github.com/Suetam016/my-agent/actions
2. Selecione: **"Executar Smart RLM (Com Early Exit)"**
3. Clique **"Run workflow"**
4. Preencha:
   - `tarefa`: "Oi, tudo bem?"
   - `contexto`: "" (vazio)
   - `modelo`: "qwen3:4b"
   - `confianca`: "0.90"
5. Clique **"Run workflow"**
6. Aguarde ~10-30 segundos
7. Veja o resultado nos logs

**Resultado esperado:**
```
[TASK] Oi, tudo bem?
[FastPath] Tentando resposta rápida
[+] EARLY EXIT! Confianca: 95%
[RESULT] Modo: fast | Confianca: 95% | Tempo: 2345ms

Oi! Tudo bem com voce? Em que posso ajudar?
```

---

### **Caminho B: Integração com Chat do PopeBot** (PRECISA DE MAIS TRABALHO)

Para fazer funcionar na web de verdade, precisaria:

1. **Encontrar hook do thepopebot** 
   - Verificar como thepopebot recebe/envia mensagens
   - Criar middleware que intercepta
   
2. **Modificar API endpoint**
   - `app/api/[...thepopebot]/route.js` atualmente só faz re-export
   - Precisaríamos criar handler customizado

3. **Chamar SmartRLM antes de thepopebot**
   ```javascript
   // ANTES: const resposta = await thepopebot(mensagem);
   // DEPOIS:
   const rlmResposta = await applySmartRLM(userId, mensagem, historico);
   if (rlmResposta) {
     return rlmResposta; // Usa SmartRLM
   }
   const resposta = await thepopebot(mensagem); // Fallback
   ```

---

## 🧪 Teste Rápido Agora

### Via CLI (na sua máquina)

```bash
python rlm/smart_rlm.py \
  --tarefa "Oi, tudo bem?" \
  --confianca 0.90 \
  --verbose
```

**Resultado esperado:**
```
[SmartRLM-1] Processing: Oi, tudo bem?...
[*] Tentando resposta rápida...
[FastPath] High confidence (95%) -> retorna imediatamente!
[+] EARLY EXIT! Confianca: 0.95
[RESULT] Modo: fast | Confianca: 95% | Tempo: 2345ms

[TASK] Oi, tudo bem?
============================================================
Oi! Tudo bem com voce? Em que posso ajudar?
============================================================
```

---

## 📝 Proximos Passos Para Teste Completo

### Step 1: Verificar como thepopebot funciona
```bash
# Procurar nos node_modules
ls node_modules/thepopebot/

# Ou verificar documentacao
npm view thepopebot
```

### Step 2: Encontrar hook de mensagem
- Ver como messages chegam
- Ver como respostas são enviadas

### Step 3: Criar wrapper customizado
```javascript
// app/api/[...thepopebot]/route.js
import { applySmartRLM } from '@/app/lib/smart_rlm_middleware.js';

export async function POST(request) {
  const body = await request.json();
  const { message, userId, history } = body;
  
  // Tenta SmartRLM
  const rlmResult = await applySmartRLM(userId, message, history);
  if (rlmResult && rlmResult.modo !== 'error') {
    return Response.json({
      resposta: rlmResult.resposta,
      metadata: { rlm: true, ...rlmResult }
    });
  }
  
  // Fallback: thepopebot normal
  const { GET, POST } = await import('thepopebot/api');
  return POST(request);
}
```

---

## 🎯 Recomendação

**Teste em 2 estágios:**

### **Stage 1: Validar SmartRLM (JÁ POSSÍVEL)**
1. Execute workflow GitHub Actions
2. Vê que Early Exit funciona
3. Vê que Full RLM funciona

### **Stage 2: Integrar com PopeBot (PRÓXIMA ETAPA)**
1. Descobrir exatamente como thepopebot funciona
2. Criar wrapper
3. Testar na web

---

## 🚀 Comece Agora

**Teste 1: GitHub Actions**
→ https://github.com/Suetam016/my-agent/actions
→ "Executar Smart RLM"
→ Escolha uma tarefa
→ Run

**Teste 2: CLI Local**
```bash
python rlm/smart_rlm.py --tarefa "Teste"
```

Manda o resultado que você vê pra eu orientar o próximo passo!

---

**Estado**: ✅ 90% pronto | ⏳ Falta integração final com thepopebot

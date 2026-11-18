# Exemplo didático: self-checkout

> Exemplo **fictício**, para mostrar o formato esperado. Não descreve uma interface real inspecionada.

## Cenário

Uma pessoa digitaliza produtos em um caixa de autoatendimento e conclui o pagamento. Após aproximar o cartão, a tela permanece parada e não oferece indicação clara de processamento.

## Achado

**IH-01 — Ausência de indicação durante o pagamento**

- **Tarefa e local:** finalizar compra → tela de pagamento.
- **Evidência:** no cenário descrito, nenhuma mensagem de processamento ou conclusão aparece depois de aproximar o cartão.
- **Impacto:** o usuário não sabe se deve aguardar, tentar novamente ou pedir ajuda; pode repetir uma ação por engano.
- **Princípios:** **N1 — Visibilidade do estado do sistema**; **S3 — Feedback informativo**; possivelmente **S4 — Encerramento claro**, se a tarefa terminar sem confirmação.
- **Severidade estimada:** **3 (grave)**, a confirmar conforme o risco de cobranças repetidas e o fluxo real.
- **Confiança:** exemplo hipotético, não observado.
- **Solução:** apresentar imediatamente um estado “Processando pagamento”, bloquear apenas a repetição da ação que causaria cobrança duplicada e exibir um desfecho inequívoco: aprovado, recusado ou não concluído; orientar o próximo passo.
- **Critério de aceite:** após iniciar o pagamento, a pessoa sempre consegue diferenciar processamento, aprovação e falha; nunca recebe incentivo ambíguo para pagar duas vezes.
- **Validação:** ensaio dos estados de pagamento com sucesso, atraso, erro e cancelamento.

## Como evitar duplicidade

Criar **um único achado IH-01** com códigos N1/S3/S4, não três problemas separados com a mesma observação. A sobreposição entre os referenciais enriquece a explicação, mas não multiplica artificialmente a contagem.

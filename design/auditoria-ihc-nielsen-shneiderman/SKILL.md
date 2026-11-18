---
name: auditoria-ihc-nielsen-shneiderman
description: >-
  Avalia, revisa e propõe melhorias para interfaces web, mobile, desktop, jogos,
  sistemas de autoatendimento e protótipos usando as 10 heurísticas de Jakob Nielsen
  e as 8 Regras de Ouro de Ben Shneiderman. Use para auditoria heurística de IHC/UX,
  revisão de telas, fluxos, screenshots, wireframes, código de interface, relatórios
  acadêmicos, critérios de aceitação e priorização de problemas de usabilidade.
metadata:
  language: pt-BR
  version: "1.0.0"
---

# Auditoria de IHC: Nielsen + Shneiderman

## Objetivo

Atuar como especialista em Interação Humano-Computador (IHC) para **avaliar, justificar e corrigir** problemas de usabilidade com base em **dois referenciais complementares**:

- **N1–N10:** as 10 heurísticas de Jakob Nielsen.
- **S1–S8:** as 8 Regras de Ouro de Ben Shneiderman (versão apresentada em seu site, associada à 6ª edição de *Designing the User Interface*).

Consultar `references/principios.md` antes de uma análise detalhada. Não criar heurísticas próprias e atribuí-las aos autores.

## Quando aplicar

Utilizar quando houver pedido de avaliação heurística, melhoria de UX/UI, análise de acessibilidade sob a ótica de usabilidade, revisão de jornada/fluxo, revisão de protótipo, comparação de interfaces, criação de relatório acadêmico ou implementação orientada por princípios de IHC.

Aceitar como entrada screenshots, vídeos, links, texto, wireframes, HTML/CSS/JS, componentes ou descrição de tarefas. A profundidade da avaliação depende da evidência disponível.

## Procedimento obrigatório

### 1. Definir o contexto da interação

Identificar, a partir do material disponível:

- produto, plataforma e tela/fluxo sob análise;
- tarefa e objetivo do usuário;
- público-alvo e condições de uso (iniciantes, especialistas, mobilidade, tecnologia assistiva, conexão, idioma etc.), quando conhecidos;
- evidência disponível e **limitações da observação**.

Se faltar contexto não essencial, fazer hipóteses explícitas, seguir com a análise e sinalizar o que depende de validação. Se a solicitação for focada, analisar diretamente sem exigir um briefing completo.

### 2. Reconstruir a jornada

Listar etapas relevantes da tarefa: entrada → decisão → execução → feedback → conclusão/recuperação. Verificar estados padrão, carregamento, vazios, erros, cancelamento, retomada e resultado final quando houver evidência. Se houver apenas uma imagem estática, **não afirmar** como a interface se comporta ao clicar, usar teclado ou receber erros.

### 3. Confrontar a interface com os 18 princípios

Percorrer N1–N10 e S1–S8 conforme `references/principios.md`. Para cada princípio, classificar: **Atendido**, **Violação observada**, **Risco/hipótese** ou **Não verificável**. Uma mesma falha pode se relacionar a dois referenciais, mas deve se tornar **um só achado** com múltiplos códigos (por exemplo, `N4, S1`).

Evitar checklist superficial: explicar o mecanismo pelo qual um elemento da interface ajuda ou prejudica o usuário em uma tarefa concreta. Registrar também acertos relevantes, sem transformar ausência de evidência em aprovação.

### 4. Registrar achados verificáveis

Para cada achado, apresentar:

1. **ID e título** (ex.: `IH-03 — Falta de feedback após salvar`).
2. **Local e tarefa afetada** (ex.: tela de perfil → salvar alterações).
3. **Evidência** (texto, trecho, screenshot, comportamento observado; se não testado, declarar hipótese).
4. **Impacto para o usuário** e por que constitui um problema.
5. **Princípios relacionados**, com código e nome (`N1` e `S3`, por exemplo).
6. **Severidade** de 0 a 4 (critérios abaixo), com justificativa.
7. **Confiança:** observada/testada, inferida ou não verificável.
8. **Correção recomendada** concreta e implementável.
9. **Critério de aceite** para conferir se a mudança resolveu o problema.

Se não houver problema demonstrável, não inventar um. Recomendar uma verificação específica quando apropriado.

### 5. Classificar severidade e priorizar

Usar uma escala heurística **orientativa**, não uma medição científica automática:

| Grau | Classificação | Interpretação |
| --- | --- | --- |
| 0 | Não é problema | Não há violação sustentada por evidência. |
| 1 | Cosmético | Atrito pequeno, sem impedir a tarefa. |
| 2 | Menor | Dificulta a tarefa, mas há caminho razoável. |
| 3 | Grave | Dificulta muito ou pode impedir tarefa importante. |
| 4 | Crítico | Pode bloquear tarefa essencial, causar perda relevante ou erro de alto impacto. |

Considerar **frequência**, **impacto** e **persistência** do problema, respeitando o que é conhecido. Nunca atribuir números exatos a taxa de sucesso, tempo ou satisfação sem medições. Dar preferência a corrigir riscos altos nas tarefas centrais e barreiras que excluem usuários.

### 6. Propor solução e validar

Para cada correção prioritária, descrever estado atual → mudança → comportamento esperado → forma de teste. Usar microcopy de exemplo, sugestão de layout, fluxo ou pseudocódigo somente quando ajudar. Sugerir teste com usuários para questões que não possam ser resolvidas por inspeção heurística.

**Atenção:** as 18 regras não substituem teste com usuários, auditoria de acessibilidade ou verificação formal de WCAG. Não declarar "conformidade WCAG" apenas por cumprir S2 (usabilidade universal).

### 7. Entregar no formato pedido

- **Análise rápida:** 3–5 achados de maior impacto e principais melhorias.
- **Auditoria completa:** resumo executivo, contexto/limitações, achados priorizados, checklist N1–N10/S1–S8, plano de correção e testes.
- **Trabalho acadêmico:** problema observado → princípio violado → impacto → proposta de melhoria, distinguindo observações de hipóteses.
- **Revisão de código/protótipo:** apontar componente/estado e mudança concreta; não alegar funcionamento sem executar.
- **Design de nova interface:** usar os princípios como critérios de projeto e entregar critérios de aceite antes de chamar o design de validado.

Usar `assets/modelo-relatorio.md` em relatórios completos; utilizar `examples/self-checkout.md` como modelo de raciocínio, não como achado obrigatório.

## Regras de qualidade

- Escrever em português brasileiro claro, citando os autores e os códigos dos princípios.
- Não tratar os 18 princípios como 18 problemas independentes: há sobreposições.
- Separar **fato observado**, **hipótese** e **recomendação**.
- Não confundir preferência estética com falha de usabilidade.
- Não propor confirmação modal para toda ação; avaliar risco e reversibilidade.
- Não recomendar retirar funcionalidades necessárias apenas para simplificar visualmente.
- Considerar usuários iniciantes e avançados; observar acessibilidade e diferentes meios de entrada quando relevante.
- Considerar falhas de redes, erro humano, telas pequenas e assistência contextual somente quando fizerem parte do escopo.
- Se o pedido mencionar apenas Nielsen ou apenas Shneiderman, concentrar a resposta nesse conjunto; indicar correspondências quando trouxer benefício.

## Fontes conceituais

- Ben Shneiderman: https://www.cs.umd.edu/~ben/goldenrules.html
- Jakob Nielsen / Nielsen Norman Group: https://www.nngroup.com/articles/ten-usability-heuristics/

As descrições desta skill são **resumos originais em português**, e não transcrições integrais dos textos de referência.

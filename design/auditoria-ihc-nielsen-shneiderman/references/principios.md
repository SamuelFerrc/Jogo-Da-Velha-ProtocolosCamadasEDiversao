# Catálogo de princípios e perguntas de inspeção

Esta referência resume os princípios para uso em auditorias. Códigos **N** = Nielsen; códigos **S** = Shneiderman. A enumeração de Shneiderman segue a versão publicada pelo autor para a 6ª edição, incluindo **usabilidade universal** na segunda regra.

## 10 Heurísticas de Jakob Nielsen

| Código | Heurística | Pergunta de avaliação | Exemplo de falha |
| --- | --- | --- | --- |
| **N1** | Visibilidade do estado do sistema | A interface informa o que está acontecendo e o resultado das ações em tempo adequado? | Salvar sem indicar conclusão, erro ou andamento. |
| **N2** | Correspondência entre sistema e mundo real | Os termos, a ordem e as metáforas fazem sentido para o público? | Mostrar nomes internos de variáveis para clientes. |
| **N3** | Controle e liberdade do usuário | É possível cancelar, voltar, sair ou desfazer ações não desejadas? | Modal sem saída clara. |
| **N4** | Consistência e padrões | Controles iguais se comportam e são nomeados de modo consistente com a plataforma? | Mesmo ícone significa ações diferentes. |
| **N5** | Prevenção de erros | A interface evita erros previsíveis antes que ocorram? | Apagar dados sem proteção proporcional ao risco. |
| **N6** | Reconhecimento em vez de memorização | Opções, instruções e informação necessária estão visíveis ou recuperáveis? | Pedir código apresentado somente na página anterior. |
| **N7** | Flexibilidade e eficiência de uso | Existem caminhos adequados a iniciantes e usuários experientes? | Fluxo repetitivo sem atalhos ou reaproveitamento. |
| **N8** | Estética e design minimalista | O conteúdo visual reforça tarefas prioritárias sem ruído desnecessário? | Informações secundárias obscurecem o botão principal. |
| **N9** | Ajudar a reconhecer, diagnosticar e recuperar erros | Mensagens dizem o que falhou e como corrigir? | Mensagem apenas “Erro 500” sem alternativa. |
| **N10** | Ajuda e documentação | É fácil encontrar orientação contextual e prática quando necessário? | Ajuda genérica desconectada da tarefa. |

## 8 Regras de Ouro de Ben Shneiderman

| Código | Regra | Pergunta de avaliação | Exemplo de falha |
| --- | --- | --- | --- |
| **S1** | Buscar consistência | A interface mantém termos, ações, posição e apresentação coerentes? | “Confirmar” ora conclui, ora apenas avança. |
| **S2** | Buscar usabilidade universal | O produto leva em conta diferentes capacidades, experiências, idades, idiomas e tecnologias? | Tarefa exige somente interação por mouse sem alternativa. |
| **S3** | Oferecer feedback informativo | A ação produz resposta perceptível proporcional à importância dela? | Pagamento processado sem mostrar status. |
| **S4** | Projetar diálogos com encerramento claro | O usuário percebe início, etapas e conclusão de cada tarefa? | Checkout termina sem confirmação do pedido. |
| **S5** | Prevenir erros | O desenho evita enganos e oferece recuperação construtiva? | Campo numérico aceita valor incompatível e perde todo o formulário. |
| **S6** | Permitir fácil reversão das ações | Há como desfazer ações ou restaurar o estado quando apropriado? | Exclusão acidental sem desfazer ou recuperar. |
| **S7** | Manter o usuário no controle | A aplicação responde às ações previsivelmente, sem impor mudanças inesperadas? | Formulário avança automaticamente sem intenção do usuário. |
| **S8** | Reduzir carga da memória de curto prazo | A pessoa não precisa reter informação entre telas desnecessariamente? | Campo exige reproduzir detalhes que desapareceram da interface. |

## Correspondências frequentes (não são equivalências perfeitas)

| Foco | Nielsen | Shneiderman | Observação |
| --- | --- | --- | --- |
| Coerência | N4 | S1 | N4 inclui convenções externas à interface. |
| Visibilidade e retorno | N1 | S3, S4 | S4 enfatiza o encerramento da sequência. |
| Controle e reversibilidade | N3 | S6, S7 | Distinguir sair/cancelar, desfazer e agência. |
| Evitar erros | N5, N9 | S5 | N9 detalha mensagens e recuperação depois da falha. |
| Memória | N6 | S8 | Reduzir necessidade de decorar e recordar. |
| Diversidade e produtividade | N7 | S2 | S2 abrange capacidades, idades, dispositivos e diferenças diversas. |
| Linguagem do usuário | N2 | S1, S2 (parcial) | Não há correspondência estrita. |
| Minimalismo | N8 | — | Não forçar pareamento. |
| Ajuda | N10 | — | Não forçar pareamento. |

## Perguntas por etapa do fluxo

- **Entrada:** a tarefa é encontrável? A terminologia é familiar? Há rótulos claros?
- **Interação:** a interface responde a ações? Os controles seguem padrões? Existem atalhos úteis?
- **Decisão:** opções e consequências estão claras? Há confirmação para ações de alto risco?
- **Erros:** a validação é adequada? Mensagens orientam a correção? Dados inseridos são preservados?
- **Saída:** há conclusão inequívoca? Cancelamento, retorno ou desfazer quando apropriados?
- **Acesso:** usuários com diferentes perfis e formas de entrada conseguem realizar o fluxo? Que aspectos exigem teste específico?

## Como selecionar um princípio

Vincular cada achado à violação mais direta. Acrescentar outros códigos apenas se explicarem **mecanismos diferentes** da mesma falha. Por exemplo: ao salvar, não mostrar confirmação é `N1/S3`; não mostrar que o processo inteiro foi concluído pode envolver `S4`, se houver uma sequência de etapas.

## Fontes

1. Ben Shneiderman, *The Eight Golden Rules of Interface Design*: https://www.cs.umd.edu/~ben/goldenrules.html
2. Jakob Nielsen, *10 Usability Heuristics for User Interface Design*, Nielsen Norman Group: https://www.nngroup.com/articles/ten-usability-heuristics/

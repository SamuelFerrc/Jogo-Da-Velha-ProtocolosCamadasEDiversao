# Skill: Auditoria de IHC — Nielsen + Shneiderman

Skill em português brasileiro para agentes de IA. Contém um `SKILL.md` conforme a estrutura de [Agent Skills](https://agentskills.io/specification), uma referência de princípios, modelo de relatório e exemplo comentado.

## Arquivos

```text
auditoria-ihc-nielsen-shneiderman/
├── SKILL.md
├── README.md
├── references/
│   └── principios.md
├── assets/
│   └── modelo-relatorio.md
└── examples/
    └── self-checkout.md
```

## Instalação genérica

Copie a pasta inteira para o diretório de skills suportado por seu agente e reinicie/atualize a descoberta de skills conforme as instruções dessa ferramenta. Mantenha os arquivos relativos juntos. O nome do diretório é o mesmo definido no frontmatter do `SKILL.md`.

## Exemplo de ativação

> Avalie este print de aplicativo usando as 10 heurísticas de Nielsen e as 8 Regras de Ouro de Shneiderman. Mostre problemas, evidências, severidade e correções.

> Analise este fluxo de self-checkout para uma apresentação de IHC. Quero problema → regra violada → impacto → solução.

> Revise o meu componente React a partir de Nielsen e Shneiderman e sugira alterações concretas, sem inventar comportamentos que não sejam visíveis no código.

## Observações

- Os princípios ajudam a inspecionar usabilidade, mas não substituem testes com pessoas usuárias.
- A auditoria não fornece certificação de acessibilidade nem garante conformidade com WCAG.
- As descrições das regras são adaptações e resumos originais com atribuição aos autores.

## Referências

- https://www.cs.umd.edu/~ben/goldenrules.html
- https://www.nngroup.com/articles/ten-usability-heuristics/

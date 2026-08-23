# Decisões de arquitetura

Este documento registra as decisões que afetam o escopo e a avaliação do challenge.

## ADR-001 - Público do agente

**Decisão:** posicionar a solução como um assistente interno para as equipes de
Atendimento e Operações da BimBam Buy.

**Motivo:** o enunciado pede um agente para colaboradores, enquanto a base fornecida
contém políticas de e-commerce voltadas ao suporte ao cliente. O agente ajuda o
colaborador a consultar essas políticas; ele não se apresenta como atendente humano e
não consulta pedidos reais.

## ADR-002 - Deploy no Streamlit Community Cloud

**Decisão:** usar o Streamlit Community Cloud em vez da OCI.

**Motivo:** os dois arquivos formais de requisitos aceitam OCI ou outra plataforma com
URL pública. O backlog é declarado como sugestivo e contém duas orientações
incompatíveis: uma frase afirma que um serviço OCI seria obrigatório, enquanto outra
afirma que nenhuma tecnologia citada é obrigatória e aceita outros provedores. A
alternativa escolhida atende aos critérios objetivos com menor complexidade.

## ADR-003 - Índice local e recuperação híbrida

**Decisão:** manter os vetores em memória e combinar similaridade semântica com TF-IDF.

**Motivo:** a base tem apenas cinco PDFs. Um banco vetorial externo acrescentaria
credenciais, custo e operação sem benefício mensurável para este volume. A interface
usa cache de recurso para evitar reconstruções dentro da mesma instância.

## ADR-004 - Gemini com fallback local

**Decisão:** usar Gemini para embeddings e geração quando `GEMINI_API_KEY` estiver
configurada, mantendo recuperação lexical e resposta extrativa quando a API estiver
indisponível.

**Motivo:** o fallback permite executar, testar e demonstrar a recuperação sem expor
segredos. O modo completo continua sendo o fluxo recomendado para o deploy.

## ADR-005 - Respostas estritamente fundamentadas

**Decisão:** o agente responde somente a partir dos trechos recuperados e exibe as
fontes. Ausência de informação resulta em uma resposta explícita de insuficiência.

**Motivo:** os documentos não fornecem contatos reais, status de pedidos, tabelas por
país nem sistemas transacionais. Inventar esses dados prejudicaria a confiabilidade.


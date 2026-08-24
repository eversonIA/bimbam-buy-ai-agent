# Decisões de arquitetura

Este documento registra as decisões que afetam o escopo e a avaliação do challenge.

## ADR-001 - Público do agente

**Decisão:** posicionar a solução como um assistente interno para as equipes de
Atendimento e Operações da BimBam Buy.

**Motivo:** o enunciado pede um agente para colaboradores, enquanto a base documental
contém políticas de e-commerce voltadas ao suporte ao cliente. O agente ajuda o
colaborador a consultar essas políticas; ele não se apresenta como atendente humano e
não consulta pedidos reais.

## ADR-002 - Deploy no Streamlit Community Cloud

**Decisão:** usar o Streamlit Community Cloud para publicar a aplicação.

**Motivo:** o challenge sugere a OCI ou outro serviço de nuvem com URL pública. O
Streamlit oferece integração direta com a aplicação, gestão segura de segredos e menor
complexidade operacional para este projeto.

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

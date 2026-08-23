# Exemplo de Backlog

## Ponto de atenção!

Todos os passos aqui são apenas sugestões da estrutura do projeto. Em outras palavras, você pode fazer o seu projeto como desejar, desde que realize as funcionalidades mencionadas em Para saber mais.

No mais, bom projeto! Qualquer dúvida use do servidor no Discord e o fórum na plataforma Alura para receber apoio em relação ao Challenge.

## Crie seu repositório de projetos no GitHub

Git e GitHub são ferramentas muito úteis para qualquer desenvolvedor, então você deve se acostumar a trabalhar com elas.

Neste desafio queremos propor que o primeiro passo a ser dado seja a criação deste repositório no GitHub.

Mesmo que você ainda não tenha desenvolvido nenhum código, o importante é que você tenha pelo menos uma pasta específica para seu projeto. e você pode atualizá-lo gradualmente.

Usemos nosso README.md para deixar bem detalhadas as funcionalidades do nosso sistema, capturas de tela e inclusive um vídeo da sua aplicação funcionando.

Desta forma você conseguirá mostrar seu projeto à comunidade 😄

## 1 - Coleta e organização de documentos

A coleta e organização dos documentos é o ponto de partida de todo o projeto: antes de processar, indexar ou buscar qualquer coisa, é preciso saber exatamente quais documentos existem, onde estão e quem é responsável por eles.

É uma etapa mais organizacional do que técnica, mas que determina a qualidade de tudo que vem depois.

1 - Mapeamento das fontes
O primeiro passo é descobrir onde os documentos relevantes estão hoje, já que numa empresa eles costumam estar espalhados:

pastas compartilhadas (Google Drive, SharePoint, OneDrive)

sistemas internos (intranet, ERP, sistema de RH)

repositórios de código (para documentação técnica)

e-mails arquivados

até pastas locais de computadores de pessoas-chave.

Esse mapeamento geralmente exige conversar com cada área (RH, Financeiro, Jurídico etc.) para entender onde guardam seus documentos oficiais.

2 - Definição de categorias
Os documentos são organizados nas categorias de negócio que fazem sentido para a empresa — como as sugeridas no início do projeto (RH, Financeiro, Operacional, Legal etc.).

Essa categorização não é apenas cosmética: ela se torna metadado usado depois para filtrar buscas e para definir responsáveis por manter aquele conjunto de documentos atualizado.

3 - Curadoria de qualidade
Nem todo documento encontrado deve entrar na base. Nessa fase é importante filtrar:

versões desatualizadas ou rascunhos (mantendo apenas a versão oficial vigente de uma política, por exemplo);

documentos duplicados ou redundantes;

conteúdo irrelevante para perguntas de colaboradores (como anotações pessoais ou arquivos de teste).

4 - Definição de responsáveis (ownership)
Cada categoria de documentos deve ter um responsável dentro da empresa — geralmente alguém da própria área (RH cuida dos documentos de RH, Jurídico cuida de contratos e compliance).

Essa pessoa é quem aprova o que entra na base e quem deve ser avisado quando o conteúdo precisar de atualização.

5 - Acesso e permissões
Como definido no projeto, o agente é aberto a todos os colaboradores, então aqui o foco não é restringir quem pode perguntar, mas garantir que o agente tenha acesso de leitura aos locais corretos (pastas, sistemas) para buscar e atualizar os documentos automaticamente, sem depender de envio manual de arquivos.

6 - Processo de ingestão inicial
Por fim, define-se como esses documentos chegarão ao pipeline de processamento (etapa 2):

via conexão direta com a fonte (API do Google Drive ou SharePoint, por exemplo);

upload manual inicial para começar o projeto;

ou uma combinação dos dois enquanto a integração automática é construída.

Por que essa etapa importa tanto
Se essa base for malfeita — com documentos desatualizados, mal categorizados ou sem responsável definido — todo o resto do pipeline (processamento, indexação, busca, geração de resposta) vai herdar esse problema.

É o princípio de "garbage in, garbage out": a IA só pode ser tão confiável quanto os documentos que alimenta.

## 2 - Processamento e extração de conteúdo

O processamento e extração de conteúdo é a fase responsável por transformar os documentos originais — em seus formatos variados — em texto limpo e estruturado, pronto para ser convertido em embeddings na etapa seguinte. Funciona mais ou menos assim:

1 - Extração por formato
Cada tipo de arquivo exige uma abordagem diferente:

PDF: extração de texto direto quando o PDF é nativo (gerado digitalmente); quando é um documento escaneado (imagem), é necessário OCR (reconhecimento óptico de caracteres) para converter a imagem em texto.

Word: extração do texto corrido, preservando estrutura como títulos e parágrafos, já que isso ajuda a manter o sentido ao dividir o conteúdo depois.

Excel: conversão das tabelas em texto estruturado (por exemplo, linha a linha, com cabeçalhos de coluna repetidos), já que planilhas têm uma lógica diferente de texto corrido.

PowerPoint: extração do texto de cada slide, geralmente junto com as notas do apresentador, que costumam ter contexto adicional importante.

Markdown, CSV, JSON, HTML: formatos já estruturados ou semiestruturados, que exigem principalmente remover marcações técnicas (tags HTML, sintaxe Markdown) mantendo o conteúdo legível, ou converter a estrutura de dados (JSON, CSV) em frases ou tabelas compreensíveis.

2 - Limpeza do texto
Remoção de ruídos que não agregam significado: cabeçalhos e rodapés repetidos, numeração de página, caracteres especiais de formatação, espaços duplicados, ou trechos corrompidos da extração (comum em PDFs malformatados).

3 - Chunking (divisão em trechos)
O texto extraído é dividido em pedaços menores (chunks), já que documentos completos costumam ser grandes demais para caber no contexto de busca e do LLM. Algumas estratégias comuns:

divisão por tamanho fixo (por exemplo, 500 a 1000 caracteres), com uma pequena sobreposição entre chunks para não cortar uma ideia no meio;

divisão por estrutura lógica do documento (por seção, por parágrafo, por slide), o que tende a preservar melhor o sentido completo de cada trecho.

4 - Atribuição de metadados
Cada chunk recebe informações que serão usadas depois para filtragem e citação de fonte: categoria do documento (RH, Financeiro etc.), nome do arquivo original, data de criação ou última atualização, autor ou responsável, e a localização exata dentro do documento (página, seção ou slide).

Por que essa etapa é crítica
A qualidade da extração e do chunking é crítica: erros nessa etapa prejudicam a busca e podem gerar respostas incompletas ou incorretas, mesmo com o restante do pipeline bem construído.

## 3 - Indexação vetorial

Indexação vetorial é o processo de transformar o texto extraído dos documentos em representações numéricas que capturam seu significado, e organizá-las de forma que possam ser buscadas rapidamente por similaridade semântica.

É o que torna possível, na etapa 4, encontrar trechos relevantes mesmo quando a pergunta do colaborador não usa exatamente as mesmas palavras do documento.

O que é um embedding
Um embedding é um vetor de números (geralmente algumas centenas ou milhares de dimensões) gerado por um modelo de linguagem treinado especificamente para isso.

Textos com significados parecidos geram vetores numericamente próximos no espaço vetorial, mesmo usando palavras diferentes.

Por exemplo, "política de reembolso de despesas" e "como pedir ressarcimento de gastos" tendem a gerar vetores próximos, porque tratam do mesmo assunto.

Como funciona nesse projeto, passo a passo
Entrada: cada chunk de texto gerado na etapa 2 (já limpo e com metadados associados) é enviado a um modelo de embedding.

Geração do vetor: o modelo retorna um vetor numérico representando aquele trecho. O mesmo modelo precisa ser usado de forma consistente para documentos e para as perguntas dos colaboradores, já que vetores gerados por modelos diferentes não são comparáveis entre si.

Armazenamento: o vetor é salvo em um banco de dados vetorial, junto com uma referência ao texto original e aos metadados (categoria, nome do arquivo, data, autor). Considerando os formatos e contextos da empresa, opções comuns incluem Pinecone, Weaviate, Qdrant, Chroma ou pgvector (extensão do PostgreSQL).

Indexação para busca eficiente: o banco vetorial organiza esses vetores em uma estrutura de índice (como HNSW — Hierarchical Navigable Small World) que permite encontrar os vetores mais próximos de uma consulta sem precisar comparar com todos os vetores armazenados um por um, o que seria inviável conforme a base de documentos cresce.

Indexação paralela de metadados: além da busca vetorial, os metadados são indexados de forma tradicional (como em qualquer banco de dados), permitindo filtros — por exemplo, restringir a busca a documentos da categoria "Financeiro" criados nos últimos 12 meses, antes mesmo de calcular similaridade semântica.

Por que isso importa
A indexação vetorial unifica documentos de formatos e categorias diferentes em um espaço de busca comum, permitindo que uma única pergunta busque em toda a base, enquanto os metadados garantem a possibilidade de restringir essa busca a um contexto específico quando necessário.

## 4 - Camada de recuperação (RAG)

A camada de recuperação é o coração do RAG: é ela que decide quais trechos de documentos serão entregues ao LLM para gerar a resposta. Funciona em algumas fases:

1 - Transformação da pergunta em embedding

Quando o colaborador faz uma pergunta, o texto dela passa pelo mesmo modelo de embedding usado na indexação dos documentos, gerando um vetor numérico que representa o significado semântico da pergunta.

2 - Busca semântica no banco vetorial

Esse vetor é comparado com os vetores de todos os trechos de documentos já indexados, usando uma métrica de similaridade (geralmente similaridade de cosseno ou distância euclidiana).

O banco vetorial retorna os N trechos mais próximos semanticamente — não necessariamente os que contêm as mesmas palavras, mas os que tratam do mesmo assunto.

Isso é o que permite que uma pergunta como "quantos dias de férias eu tenho?" encontre um trecho que fala em "política de licença remunerada" mesmo sem usar a palavra "férias".

3 - Filtragem por metadados
Antes ou depois da busca semântica, é comum aplicar filtros usando os metadados definidos na etapa 2 — por exemplo, restringir a busca apenas a documentos da categoria "RH" ou aos mais recentes, descartando versões antigas de uma política já revisada.

4 - Reranqueamento
A busca vetorial inicial costuma retornar um número maior de candidatos (por exemplo, os 20 trechos mais próximos) para depois passar por um segundo modelo, mais preciso porém mais lento, chamado reranker.

Esse modelo reavalia cada candidato considerando a pergunta completa e reordena os resultados por relevância real, retendo apenas os mais úteis (por exemplo, os 3 a 5 melhores).

5 - Montagem do contexto
Os trechos finais selecionados são organizados em um bloco de texto, junto com seus metadados de origem (documento, seção, data), formando o contexto que será inserido no prompt enviado ao LLM na etapa de geração de resposta.

Por que o reranqueamento importa
A busca vetorial pura é rápida mas pode trazer resultados levemente fora do alvo, já que mede similaridade geral de significado.

O reranker corrige isso analisando a relação mais detalhada entre pergunta e trecho, melhorando bastante a precisão final — é um equilíbrio entre velocidade (busca vetorial ampla) e qualidade (reranqueamento sobre um conjunto reduzido).

## 5 - Geração e validação de respostas

O LLM recebe a pergunta mais o contexto recuperado e gera uma resposta baseada nos documentos, sempre indicando a fonte (nome do arquivo, seção ou página).

Quando o conteúdo necessário não é encontrado, o agente deve informar claramente em vez de inventar uma resposta.

1 - Geração da resposta
Depois que a etapa de recuperação encontra os trechos de documentos mais relevantes para a pergunta, esses trechos são inseridos em um prompt junto com a pergunta original e enviados ao LLM.

O prompt geralmente instrui o modelo a responder somente com base no contexto fornecido, sem usar conhecimento externo, e a indicar claramente de qual documento cada informação foi extraída.

2 - Citação da fonte
Para que a resposta seja rastreável e verificável, o agente anexa metadados de origem: nome do arquivo, seção, página ou data de atualização.

Isso permite que o colaborador confirme a informação no documento original, o que é especialmente importante em áreas sensíveis como Legal, Financeiro ou RH.

3 - Validação e controle de alucinação
Para reduzir o risco de o modelo inventar informações, algumas técnicas comuns são:

restringir o modelo a responder apenas com base no contexto recuperado, instruindo-o a admitir quando não souber;

comparar a resposta gerada com os trechos originais (verificação de consistência), rejeitando ou regenerando respostas que não tenham respaldo claro no contexto;

definir um limiar de confiança na busca semântica: se nenhum trecho recuperado tiver relevância suficiente, o agente não tenta gerar resposta.

4 - Fallback quando não há resposta
Quando os documentos disponíveis não cobrem a pergunta, o agente deve informar isso explicitamente ("não encontrei essa informação nos documentos disponíveis") em vez de arriscar uma resposta incorreta, e pode sugerir o contato com a área responsável (RH, Jurídico etc.) ou indicar que aquele tipo de pergunta está fora do escopo da base de conhecimento.

→ Aqui você deve revisar se os contatos das áreas estão no banco de informações conhecidas pelo o agente.

5 - Formatação final
Por fim, a resposta é estruturada de forma clara para o colaborador, normalmente incluindo um resumo direto seguido das referências aos documentos usados, podendo variar conforme o canal (chat, e-mail, integração com Teams/Slack).

## 6 - Implantação, interface e manutenção

O agente precisa de uma interface acessível (chat web, integração com Slack ou Teams, por exemplo).

→ Vale reforçar que a interface não precisa ter um design e front-end profissional, isto não é o foco do projeto, foque numa interface simples mas funcional, isso é o suficiente.

Construção da interface
A escolha do canal depende de onde os colaboradores já trabalham no dia a dia:

Chat web dedicado: uma página interna simples, geralmente a opção mais rápida de implementar, com campo de pergunta, histórico de conversa e exibição das fontes citadas.

Integração com ferramentas de comunicação: um bot dentro do Microsoft Teams ou Slack, que é a opção mais natural quando a empresa já usa essas plataformas para o trabalho diário, evitando que o colaborador precise abrir mais um sistema.

Plugin em sistemas existentes: incorporar o agente como um widget dentro da intranet corporativa ou portal de RH já existente.

Independentemente do canal, alguns elementos de interface são importantes:

indicação clara de que está conversando com um agente de IA (não uma pessoa);

exibição das fontes/documentos usados em cada resposta;

um botão de feedback (positivo/negativo) em cada resposta;

um histórico de conversa para dar continuidade ao contexto dentro de uma sessão.

Manutenção contínua
Aqui entram os processos que mantêm o agente relevante e confiável depois do lançamento:

Pipeline de atualização de documentos: sempre que um documento for criado, alterado ou removido nas fontes originais, esse pipeline deve detectar a mudança, reprocessar o arquivo e atualizar o índice vetorial automaticamente (ou em uma rotina periódica, como diária ou semanal).

Curadoria de conteúdo: um responsável por cada categoria (RH, Financeiro etc.) deve revisar periodicamente se os documentos indexados ainda são a versão oficial, evitando que o agente responda com base em uma política antiga, por exemplo.

Monitoramento de qualidade: acompanhar métricas como taxa de perguntas sem resposta, feedback negativo dos colaboradores e tempo de resposta, usando essas informações para identificar lacunas na base de documentos.

Ciclo de melhoria: perguntas recorrentes sem boa resposta podem indicar a necessidade de adicionar um novo documento à base, e respostas mal avaliadas podem indicar ajustes necessários no prompt ou na lógica de recuperação.

Atualização do modelo: avaliar periodicamente se uma nova versão do LLM traz melhoria de qualidade, sempre testando antes de substituir o modelo em produção.

Esse ciclo de manutenção é o que garante que o agente continue confiável conforme a empresa cresce e os documentos mudam, em vez de virar um sistema desatualizado pouco tempo depois do lançamento.

Temos um artigo que pode ajudar na hora de fazer a interface do projeto caso você escolha usar Streamlit para isso: Streamlit: como compartilhar sua aplicação de dados facilmente | Alura

## 7 - Deploy na nuvem OCI

Com o agente validado localmente nos passos anteriores, esta etapa cobre a publicação do sistema na Oracle Cloud Infrastructure, tornando-o acessível a todos os colaboradores de forma estável e escalável. Neste caso, segue sugestões de configurações e serviços OCI:

Containerização: empacotar a aplicação (API do agente, lógica de RAG, dependências) em uma imagem Docker, armazenada no OCI Container Registry (OCIR).

Compute: optar entre OCI Compute (instâncias VM simples), Container Instances (execução de containers sem gerenciar VM) ou OKE — Oracle Kubernetes Engine, para orquestração com escalonamento automático conforme o volume de perguntas.

Armazenamento de documentos: os arquivos originais (PDF, Word, Excel etc.) ficam no OCI Object Storage, com controle de acesso via políticas do IAM da OCI.

Banco vetorial: pode ser hospedado no Oracle Autonomous Database (que suporta busca vetorial nativa) ou em uma solução vetorial dedicada rodando sobre Compute/OKE, mantendo os embeddings sincronizados com os documentos do Object Storage.

Segredos e credenciais: chaves de API (do LLM, por exemplo) e strings de conexão ficam no OCI Vault, nunca expostas em variáveis de ambiente abertas.

Rede e segurança: configuração de uma Virtual Cloud Network (VCN) com subnets públicas/privadas, Load Balancer para distribuir requisições e Network Security Groups controlando o tráfego permitido.

CI/CD: pipeline (OCI DevOps ou GitHub Actions) que builda a imagem, executa testes e faz o deploy automático a cada atualização do código ou dos documentos indexados.

O que é Deploy? Nesse contexto, é o processo de colocar o agente de IA em funcionamento em um ambiente real e acessível, em vez de mantê-lo apenas rodando na máquina do desenvolvedor (localmente) durante testes.

→ Lembre-se que nenhuma tecnologia ou serviço mencionado é obrigatório de usar. Porém, é obrigatório usar ao menos 1 serviço do ecossistema OCI neste processo de deploy.

## 8 - Registrar execução do projeto

O registro de execução documenta o que o agente faz em produção (ou em testes), permitindo auditoria, depuração e melhoria contínua.

Lembrando que é necessário executar em nuvem e adicionar qualquer mídia, foto ou vídeo, como registro desta execução.

A forma de fazer isso muda conforme o ambiente:

Execução local
Quando o agente roda na máquina do desenvolvedor ou em um servidor interno sem orquestração de nuvem, o registro tende a ser simples e direto:

Logs: gravados em arquivos locais, geralmente em formato JSON Lines, contendo pergunta, contexto recuperado, resposta gerada, timestamp e tempo de resposta.

Versionamento: uso de Git para o código e ferramentas como DVC (Data Version Control) para rastrear versões dos documentos indexados e dos embeddings gerados.

(Opcional) Monitoramento: pode ser feito com um dashboard simple, lido diretamente dos arquivos de log, sem necessidade de infraestrutura adicional.

Vantagens: baixo custo, controle total sobre os dados, ideal para protótipos e POCs.

Limitações: não escala automaticamente, sem alta disponibilidade, e a responsabilidade por backups e segurança é manual.

Execução em nuvem
Quando o agente é implantado em um provedor de nuvem (AWS, GCP, Azure) ou plataforma gerenciada, o registro se torna mais robusto e centralizado:

Logs: centralizados em serviços como CloudWatch, Azure Monitor ou Google Cloud Logging, permitindo busca, retenção configurável e alertas automáticos.

Versionamento: registros das versões de modelos, prompts, índices vetoriais e parâmetros de cada execução, possibilitando comparar desempenho entre versões.

(Opcional) Monitoramento: dashboards de observabilidade acompanham métricas como latência, taxa de erro, custo por requisição e uso de tokens, com alertas automáticos em caso de anomalias.

Vantagens: escalabilidade automática, alta disponibilidade, integração nativa com pipelines de CI/CD e backups geridos pelo provedor.

Limitações: custo recorrente, maior complexidade de configuração e necessidade de governança sobre dados sensíveis trafegando externamente.

→ Nenhuma tecnologia ou ferramenta mencionada é obrigatória, fica a seu critério usar elas. A obrigação é apenas registrar a execução em nuve;

Em ambos os casos, o objetivo final é o mesmo: garantir rastreabilidade (quem perguntou o quê, qual documento foi usado, qual resposta foi dada) e dados suficientes para auditar decisões e melhorar o agente com o tempo.

## Faça um README

Um dos passos mais importantes ao participar de um processo seletivo é resolver um desafio proposto pela empresa e geralmente isso deve estar descrito no README.

E o que é o README? É um arquivo com extensão .md e é um documento com a descrição do projeto.

Agora que estamos na reta final do projeto, vamos começar a desenvolver arquivos README para nossos últimos desafios.

## Finalizar o Curso

Agora com o seu projeto pronto, não se esqueça de enviar o link do seu repositório do GitHub no curso do desafio e baixar o certificado!
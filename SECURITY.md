# Segurança

## Segredos

- Nunca faça commit de `.env` ou `.streamlit/secrets.toml`.
- Use `.env.example` apenas como referência de nomes.
- No Streamlit Community Cloud, cadastre `GEMINI_API_KEY` nas configurações de
  segredos da aplicação.
- Revogue e substitua imediatamente qualquer chave publicada por engano.
- Configure limites de uso e alertas no provedor da API antes de divulgar a URL.

## Dados

A versão de demonstração usa apenas os documentos fictícios fornecidos no challenge.
Ela não deve receber senhas, CVV, número completo de cartão, documentos pessoais,
comprovantes ou dados reais de clientes.

## Relato de vulnerabilidade

Não abra uma issue pública com um segredo ou dado pessoal. Revogue primeiro a
credencial afetada e contate o responsável pelo repositório de forma privada.


"""Interface web do BimBam Buy Knowledge Agent."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from bimbam_agent.agent import build_knowledge_agent
from bimbam_agent.config import Settings
from bimbam_agent.models import AgentAnswer, SearchResult

SUGGESTED_QUESTIONS = (
    "Quais formas de pagamento são aceitas?",
    "Como funciona o prazo para solicitar uma devolução?",
    "O que a garantia cobre?",
    "Como acompanho o envio do meu pedido?",
)


def _secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        return None
    return str(value).strip() if value else None


@st.cache_resource(show_spinner="Preparando a base de conhecimento…")
def _cached_agent(settings: Settings):
    return build_knowledge_agent(settings)


def _settings() -> Settings:
    settings = Settings.from_env()
    api_key = settings.gemini_api_key or _secret("GEMINI_API_KEY")
    model = _secret("GEMINI_MODEL") or settings.generation_model
    embedding_model = _secret("GEMINI_EMBEDDING_MODEL") or settings.embedding_model
    return replace(
        settings,
        gemini_api_key=api_key,
        generation_model=model,
        embedding_model=embedding_model,
    )


def _source_card(number: int, result: SearchResult) -> None:
    chunk = result.chunk
    st.markdown(f"**Fonte {number} · {chunk.citation}**")
    st.caption(f"Categoria: {chunk.category} · pontuação relativa: {result.score:.2f}")
    st.write(chunk.text)


def _render_answer(answer: AgentAnswer, *, message_key: str) -> None:
    st.markdown(answer.text)
    labels = {
        "gemini": "Resposta sintetizada pelo Gemini",
        "extrativo": "Resposta extrativa local",
        "extrativo (fallback)": "Gemini indisponível; resposta extrativa local",
        "sem_resultados": "Nenhuma evidência relevante encontrada",
        "dados_ao_vivo_indisponiveis": "Consulta a sistema externo não disponível",
    }
    st.caption(labels.get(answer.mode, answer.mode.replace("_", " ").capitalize()))
    if answer.sources:
        with st.expander(f"Ver fontes consultadas ({len(answer.sources)})"):
            for number, result in enumerate(answer.sources, start=1):
                _source_card(number, result)
                if number != len(answer.sources):
                    st.divider()

    feedback = st.feedback("thumbs", key=f"feedback-{message_key}")
    if feedback is not None:
        st.caption("Obrigado pelo feedback.")


def _render_history() -> None:
    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            answer = message.get("answer")
            if isinstance(answer, AgentAnswer):
                _render_answer(answer, message_key=str(index))
            else:
                st.markdown(message["content"])


def _conversation_for_agent() -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for message in st.session_state.messages[-8:]:
        content = message.get("content", "")
        if content:
            history.append({"role": message["role"], "content": content})
    return history


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #fbfaf7; }
        [data-testid="stHeader"] { background: rgba(251, 250, 247, .85); }
        [data-testid="stSidebar"] { background: #17251f; }
        [data-testid="stSidebar"] * { color: #f6f1df; }
        .brand-kicker {
            color: #dd6b38; font-size: .78rem; font-weight: 800;
            letter-spacing: .13em; margin-bottom: .35rem; text-transform: uppercase;
        }
        .brand-title { color: #173c2d; font-size: 2.35rem; line-height: 1.08; margin: 0; }
        .brand-copy { color: #50635a; font-size: 1rem; margin: .6rem 0 1.4rem; }
        [data-testid="stChatMessage"] {
            background: #ffffff; border: 1px solid #e5e7df; border-radius: 16px;
            box-shadow: 0 3px 14px rgba(23, 60, 45, .04); padding: .35rem .7rem;
        }
        .stButton > button { border-radius: 999px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="BimBam Buy · Assistente",
        page_icon="🛍️",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    _apply_theme()

    settings = _settings()
    with st.sidebar:
        st.markdown("## 🛍️ BimBam Buy")
        st.caption("Assistente de políticas e procedimentos")
        st.divider()
        if settings.gemini_api_key:
            st.success(f"Gemini configurado · {settings.generation_model}")
        else:
            st.warning(
                "Modo sem Gemini: as respostas exibem trechos recuperados diretamente "
                "dos documentos. Configure `GEMINI_API_KEY` para habilitar a síntese."
            )
        st.caption("A IA pode cometer erros. Confirme decisões importantes nas fontes.")
        st.divider()
        if st.button("Limpar conversa", use_container_width=True, icon="🗑️"):
            st.session_state.messages = []
            st.rerun()

    st.markdown(
        '<div class="brand-kicker">Assistente de IA · Base de conhecimento</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<h1 class="brand-title">Como podemos ajudar?</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="brand-copy">Pergunte sobre pagamentos, envios, garantia, devoluções '
        "ou o programa de afiliados. Cada resposta mostra as evidências utilizadas.</p>",
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    try:
        agent = _cached_agent(settings)
    except Exception as exc:
        st.error(
            "Não foi possível preparar a base documental. Confira os arquivos e tente novamente."
        )
        with st.expander("Detalhes técnicos"):
            st.code(f"{type(exc).__name__}: {exc}")
        st.stop()

    _render_history()

    selected_question: str | None = None
    if not st.session_state.messages:
        st.caption("Experimente uma destas perguntas:")
        columns = st.columns(2)
        for index, suggestion in enumerate(SUGGESTED_QUESTIONS):
            with columns[index % 2]:
                if st.button(suggestion, key=f"suggestion-{index}", use_container_width=True):
                    selected_question = suggestion

    typed_question = st.chat_input(
        "Digite sua pergunta sobre a BimBam Buy",
        max_chars=1_000,
    )
    question = selected_question or typed_question
    if not question:
        return

    history = _conversation_for_agent()
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🛍️"):
        with st.spinner("Consultando os documentos…"):
            try:
                answer = agent.ask(question, history=history)
            except Exception:
                error_message = "Não consegui concluir a consulta. Tente novamente em instantes."
                st.error(error_message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message, "avatar": "🛍️"}
                )
                return
        _render_answer(answer, message_key=str(len(st.session_state.messages)))

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer.text,
            "answer": answer,
            "avatar": "🛍️",
        }
    )


if __name__ == "__main__":
    main()

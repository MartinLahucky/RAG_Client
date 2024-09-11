import asyncio
import streamlit as st
from logger import setup_logging

# Inicializace session state pro jazyk a historii
if 'language' not in st.session_state:
    st.session_state.language = 'cs'  # Výchozí jazyk

if 'history' not in st.session_state:
    st.session_state.history = []  # Inicializace historie jako prázdný seznam

# Konfigurace stránky - musí být první Streamlit příkaz
st.set_page_config(page_title="RAG4u", layout="wide")

import settings
import utils
from openai import OpenAI
from dotenv import load_dotenv
import os
from fill_db import load_and_process_documents
from utils import get_mongodb_client


utils.setup_directories()
load_dotenv()

async def load_database():
    await load_and_process_documents()

db = get_mongodb_client()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_relevant_documents(query, n_results):
    results = db.search_documents('data', query, n_results)
    return results

def get_openai_response(system_prompt, user_query, relevant_docs):
    context = "\n".join([doc['content'] for doc in relevant_docs])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {user_query}"}
    ]

    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=messages
    )
    return response.choices[0].message.content, response

st.title(settings.t("title"))

st.sidebar.header(settings.t("configuration"))
n_results = st.sidebar.slider(settings.t("num_results"), 1, 5, 1)

languages = ["en", "cs"]
selected_language = st.sidebar.selectbox(
    settings.t("current_language"),
    languages,
    format_func=lambda x: "English" if x == "en" else "Čeština",
    index=languages.index(st.session_state.language)
)
st.session_state.language = selected_language

# Zobrazení historie dotazů v session
st.sidebar.markdown("---")
st.subheader(settings.t("session_history"))
for entry in st.session_state.history:
    st.write(f"**{settings.t('query')}:** {entry['query']}")
    st.write(f"**{settings.t('ai_response')}:** {entry['response']}")

# Uživatelský vstup pro dotaz
query = st.text_input(settings.t("enter_question"))

# Zpracování dotazu a odpovědí při kliknutí na tlačítko Odeslat
if st.button(settings.t("submit")):
    if query:
        with st.spinner(settings.t("searching")):
            relevant_docs = get_relevant_documents(query, n_results)

            system_prompt = f"""
            You are a helpful assistant. You answer questions based only on the knowledge I'm providing you.
            You don't use your internal knowledge and you don't make things up.
            If you don't know the answer, you can say "I don't know" or "Nevím". Always answer in Czech.
            """
            response_content, response = get_openai_response(system_prompt, query, relevant_docs)
            st.session_state.history.append({
                "query": query,
                "response": response_content,
                "tokens": [doc['metadata']['tokens'] for doc in relevant_docs],
                "sources": [doc['metadata']['source'] for doc in relevant_docs]
            })
            st.write(response_content)
    else:
        st.warning(settings.t("warning"))

# Tlačítko pro zobrazení odpovědi s tokeny a zdroji
if st.button(settings.t("show_history")):
    if st.session_state.history:
        last_entry = st.session_state.history[-1]
        st.write(f"**{settings.t('query')}:** {last_entry['query']}")
        st.write(f"**{settings.t('ai_response')}:** {last_entry['response']}")
        st.write(f"**Tokens:** {last_entry['tokens']}")
        st.write(f"**Sources:** {last_entry['sources']}")
    else:
        st.warning(settings.t("no_history"))

if __name__ == "__main__":
    setup_logging()
    asyncio.run(load_database())
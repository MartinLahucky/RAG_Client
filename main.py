import streamlit as st
import settings
import utils

# Kontrola, zda byla nastavena konfigurace stránky
if not hasattr(st, '_page_config_set'):
    st.set_page_config(page_title=settings.t("title"), layout="wide")
    st._page_config_set = True

from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from fill_db import load_and_process_documents
from utils import get_mongodb_client

# Todo Features
# Automatické setupování všech potřebných složek
# Nahrávání dokumentů za běhu
# Nastavení počtu výsledků
# Rozšíření otázek, ne limit jedné odpovědi
# Přidávní více modelů
# Fix lokalizace

utils.setup_directories()
load_dotenv()



if 'language' not in st.session_state:
    st.session_state.language = 'cs'

def initialize_database():
    load_and_process_documents()

db = get_mongodb_client()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_openai_response(system_prompt, user_query):
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    )
    return response.choices[0].message.content

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

query = st.text_input(settings.t("enter_question"))

if st.button(settings.t("submit")):
    if query:
        with st.spinner(settings.t("searching")):
            results = db.search_documents('pdfs', query, n_results)

            # Převeední ObjectId na string
            for result in results:
                if '_id' in result:
                    result['_id'] = str(result['_id'])

            system_prompt = f"""
            You are a helpful assistant. You answer questions based only on the knowledge I'm providing you.
            You don't use your internal knowledge and you don't make things up.
            If you don't know the answer, you can say "I don't know".
            The data:
            {json.dumps(results)}
            """

            ai_response = get_openai_response(system_prompt, query)

            st.subheader(settings.t("ai_response"))
            st.write(ai_response)

            with st.expander(settings.t("show_results")):
                for i, doc in enumerate(results):
                    st.write(settings.t("result") + f" {i + 1}:")
                    st.json(doc['metadata'])
                    st.text(doc['content'])
    else:
        st.warning(settings.t("warning"))

st.sidebar.markdown("---")

if __name__ == "__main__":
    initialize_database()
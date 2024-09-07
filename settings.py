import json
import os
import streamlit as st
from utils import get_mongodb_client

db = get_mongodb_client()

def load_translations():
    with open('settings/localization.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def t(key):
    return db.get_translation(key, st.session_state.language)

def load_settings():
    settings = db.query_documents('settings', {"type": "app_settings"}, limit=1)
    if settings:
        return settings[0]
    return {}

def save_settings(settings):
    db.update_document('settings', {"type": "app_settings"}, settings)

def on_language_change():
    st.experimental_rerun()

def settings_ui():
    settings = load_settings()
    st.header(t('settings_title'))

    language = st.sidebar.selectbox(
        t('language_select'),
        options=['cs', 'en'],
        format_func=lambda x: "Čeština" if x == 'cs' else "English",
        key='language',
        on_change=on_language_change
    )

    n_results = st.slider(t('num_results'), 1, 10, value=settings.get('n_results', 5))
    db_path = st.text_input(t('db_path'), value=settings.get('db_path', os.getenv("MONGODB_URI")))
    openai_model = st.text_input(t('openai_model'), value=settings.get('openai_model', 'gpt-4o'))
    log_errors = st.checkbox(t('log_errors'), value=settings.get('log_errors', False))

    if st.button(t('save_settings')):
        new_settings = {
            'language': language,
            'n_results': n_results,
            'db_path': db_path,
            'openai_model': openai_model,
            'log_errors': log_errors,
            'type': 'app_settings'
        }
        save_settings(new_settings)
        st.success(t('settings_saved'))

    return settings

def main():
    settings = settings_ui()

if __name__ == "__main__":
    main()
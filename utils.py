import hashlib

from database import MongoDB
import streamlit as st
import unicodedata
import re
import os

@st.cache_resource
def get_mongodb_client():
    return MongoDB()

def remove_diacritics(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def normalize_spaces(input_str):
    return re.sub(r'\s+', '_', input_str).strip()

def rename_files_in_directory(directory):
    for filename in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, filename)):
            new_filename = remove_diacritics(filename)
            new_filename = normalize_spaces(new_filename)
            os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))


def setup_directories():
    directories = ['logs', 'data', 'outputs']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory '{directory}' created.")
        else:
            print(f"Directory '{directory}' already exists.")


def reload_localization():
    db = MongoDB()
    db.reload_localization()
    db.close_connection()

def calculate_file_hash(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

if __name__ == "__main__":
    db = get_mongodb_client()
    db.clear_all_data()
    reload_localization()
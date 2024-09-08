import os
import time
from typing import Dict, List, Any
import fitz
import magic
import pandas as pd
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pptx import Presentation
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import logger
import tokenizer
from database import MongoDB


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, process_function):
        self.process_function = process_function

    def on_created(self, event):
        if not event.is_directory:
            logger.log_info(f"Nový soubor detekován: {event.src_path}")
            self.process_function()


def monitor_directory(directory, process_function):
    event_handler = NewFileHandler(process_function)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def convert_metadata(metadata):
    converted = {}
    for key, value in metadata.items():
        if key in ['tokens', 'pos_tags', 'named_entities']:
            converted[key] = value
        elif isinstance(value, (list, tuple)):
            converted[key] = str(value)
        elif isinstance(value, (str, int, float, bool)):
            converted[key] = value
        else:
            converted[key] = str(value)
    return converted


def split_text(raw_documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )

    if isinstance(raw_documents, list):
        if isinstance(raw_documents[0], dict):
            texts = [doc['page_content'] for doc in raw_documents]
        else:
            texts = raw_documents
    else:
        texts = [raw_documents]

    split_texts = []
    for text in texts:
        split_texts.extend(text_splitter.split_text(text))

    return [{"page_content": text} for text in split_texts]


def get_file_type(file_path):
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)

    # Fallback na detekci podle přípony
    if file_type == 'application/octet-stream':
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()
        if extension == '.pdf':
            return 'application/pdf'
        elif extension in ['.doc', '.docx']:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif extension in ['.xls', '.xlsx']:
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif extension in ['.ppt', '.pptx']:
            return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

    return file_type


def extract_text_from_pdf(file_path):
    try:
        document = fitz.open(file_path)
        text = ""
        for page in document:
            text += page.get_text()
        document.close()
        return [{"page_content": text}]  # Balení textu do slovníku
    except Exception as e:
        logger.log_warning(f"Error reading {file_path}: {e}")
        return []


def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
        if not text.strip():  # Kontrola, zda text není prázdný
            logger.log_warning(f"Extrahovaný text z DOCX {file_path} je prázdný.")
            return []
        return [{"page_content": text}]
    except Exception as e:
        logger.log_warning(f"Chyba při extrakci textu z DOCX {file_path}: {str(e)}")
        return []


def extract_text_from_pptx(file_path):
    try:
        prs = Presentation(file_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return [{"page_content": '\n'.join(text)}]
    except Exception as e:
        logger.log_warning(f"Chyba při extrakci textu z PPTX {file_path}: {str(e)}")
        return []


def extract_text_from_xlsx(file_path):
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        text = df.to_string(index=False)
        return [{"page_content": text}]
    except Exception as e:
        logger.log_warning(f"Chyba při extrakci textu z XLSX {file_path}: {str(e)}")
        return []


def extract_text_from_txt(file_path: str) -> List[Dict[str, str]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return [{"page_content": content}]
    except Exception as e:
        logger.log_warning(f"Error reading text file {file_path}: {str(e)}")
        return []


def process_file(file_path: str, file_type: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        logger.log_warning(f"File not found: {file_path}")
        return []

    try:
        if 'pdf' in file_type:
            return extract_text_from_pdf(file_path)
        elif 'wordprocessingml.document' in file_type:
            return extract_text_from_docx(file_path)
        elif 'presentationml.presentation' in file_type:
            return extract_text_from_pptx(file_path)
        elif 'spreadsheetml.sheet' in file_type:
            return extract_text_from_xlsx(file_path)
        elif 'text/plain' in file_type:
            return extract_text_from_txt(file_path)
        else:
            logger.log_warning((f"Unsupported file type: {file_type} for file: {file_path}"))
            return []
    except Exception as e:
        logger.log_warning((f"Error processing file {file_path}: {str(e)}"))
        return []


def process_paragraph(paragraph, file_path):
    page_content = paragraph['page_content']
    tokens = tokenizer.tokenize_text(page_content)
    pos_tags = tokenizer.pos_tag(tokens)
    named_entities = tokenizer.named_entity_recognition(pos_tags)

    metadata = {
        "tokens": tokens,
        "pos_tags": pos_tags,
        "named_entities": named_entities,
        "source": file_path,
        "page": paragraph.get("page", 0)
    }

    converted_metadata = convert_metadata(metadata)

    return {
        "content": page_content,
        "metadata": converted_metadata
    }


# Funkce pro načtení a zpracování dokumentů ve složce "data"
def load_and_process_documents():
    logger.log_info("Zpracování dokumentů ve složce 'data'...")
    db = MongoDB()  # Připojení k MongoDB
    db.reload_localization()  # Načtení lokalizací

    documents = []
    for root, dirs, files in os.walk('data'):
        for file in files:
            file_path = os.path.join(root, file)
            file_type = get_file_type(file_path)
            try:
                raw_documents = process_file(file_path, file_type)
                if not raw_documents:
                    logger.log_warning(f"Žádný obsah nebyl extrahován z {file_path}")
                    continue

                paragraphs = split_text(raw_documents)

                for paragraph in paragraphs:
                    document = process_paragraph(paragraph, file_path)
                    documents.append(document)

            except Exception as e:
                logger.log_warning(f"Chyba při zpracování souboru {file}: {str(e)}")

    db.insert_documents('data', documents)
    db.create_text_index('data', 'content')
    db.close_connection()
    logger.log_info("Dokumenty byly zpracovány a uloženy do databáze.")


if __name__ == "__main__":
    data_directory = 'data'
    if not os.path.exists(data_directory):
        os.makedirs(data_directory)
    monitor_directory(data_directory, load_and_process_documents)

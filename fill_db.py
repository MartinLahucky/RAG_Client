from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tokenizer
from database import MongoDB
from utils import rename_files_in_directory
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import os

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, process_function):
        self.process_function = process_function

    def on_created(self, event):
        if not event.is_directory:
            print(f"New file detected: {event.src_path}")
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
    for key, value in metadata.items():
        if isinstance(value, list):
            metadata[key] = str(value)
        elif not isinstance(value, (str, int, float, bool)):
            metadata[key] = str(value)
    return metadata

def load_and_process_documents():
    tokenizer.setup_ssl()
    tokenizer.download_nltk_data()

    db = MongoDB()
    db.reload_localization()  # Todo Smazat po finalizaci textů

    # Rename files in the 'data' directory
    rename_files_in_directory('data')

    loader = PyPDFDirectoryLoader('data')
    raw_documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        length_function=len,
        is_separator_regex=True,
        separators=["\\n\\n", "\\n", "\\.", "!", "\\?"]
    )

    paragraphs = text_splitter.split_documents(raw_documents)

    documents = []

    for paragraph in paragraphs:
        tokens = tokenizer.tokenize_text(paragraph.page_content)
        pos_tags = tokenizer.pos_tag(tokens)
        named_entities = tokenizer.named_entity_recognition(pos_tags)

        document = {
            "content": paragraph.page_content,
            "metadata": convert_metadata({
                "tokens": tokens,
                "pos_tags": pos_tags,
                "named_entities": str(named_entities),
                "source": paragraph.metadata.get("source", ""),
                "page": paragraph.metadata.get("page", 0)
            })
        }
        documents.append(document)

    db.insert_documents('pdfs', documents)
    db.create_text_index('pdfs', 'content')
    db.close_connection()

if __name__ == "__main__":
    data_directory = 'data'
    if not os.path.exists(data_directory):
        os.makedirs(data_directory)
    monitor_directory(data_directory, load_and_process_documents)
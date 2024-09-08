import json
import os
import uuid
from datetime import timedelta, datetime
import pymongo
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

import logger

load_dotenv()


class MongoDB:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.client[os.getenv("MONGODB_DB_NAME", "pdf_qa_db")]
        self.ensure_indexes()

    def ensure_indexes(self):
        collection = self.db['data']

        # Kontrola existujících indexů
        indexes = collection.index_information()
        if "metadata.file_hash_1" not in indexes:
            collection.create_index([("metadata.file_hash", pymongo.ASCENDING)], unique=True)
            logger.log_info("Index 'metadata.file_hash_1' byl vytvořen.")

        # Toto by mělo být prováděno jen výjimečně nebo v údržbě
        # Najdeme duplicity v file_hash
        duplicates = collection.aggregate([
            {"$group": {"_id": "$metadata.file_hash", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ])

        # Oprava duplicitních file_hash hodnot
        for dup in duplicates:
            logger.log_warning(f"Duplicate found: {dup['_id']} with {dup['count']} occurrences.")

            # Najdeme všechny dokumenty s duplicitním file_hash
            duplicate_docs = collection.find({"metadata.file_hash": dup["_id"]})

            # Pro každý duplicitní dokument vygenerujeme unikátní hash
            for doc in duplicate_docs:
                unique_hash = str(uuid.uuid4())
                logger.log_info(f"Updating document ID {doc['_id']} with new file_hash: {unique_hash}")
                collection.update_one({"_id": doc["_id"]}, {"$set": {"metadata.file_hash": unique_hash}})

    def get_collection(self, collection_name):
        return self.db[collection_name]

    def insert_documents(self, collection_name, documents):
        collection = self.db[collection_name]

        for doc in documents:
            # Kontrola, zda existuje 'file_hash' v 'metadata'
            file_hash = doc['metadata'].get('file_hash', None)

            if not file_hash:
                # Pokud 'file_hash' chybí, zaloguj to nebo nastav výchozí hodnotu
                file_hash = str(uuid.uuid4())  # Nebo jiná logika pro generování výchozího hash
                doc['metadata']['file_hash'] = file_hash  # Přidej 'file_hash' do dokumentu

            # Vloží nebo aktualizuje dokument s podmínkou na file_hash
            collection.replace_one({"metadata.file_hash": file_hash}, doc, upsert=True)

    def query_documents(self, collection_name, query, limit=1):
        collection = self.get_collection(collection_name)
        return list(collection.find(query).limit(limit))

    def insert_document(self, collection_name, document):
        collection = self.db[collection_name]

        # Kontrola, zda existuje 'file_hash' v 'metadata'
        file_hash = document['metadata'].get('file_hash', None)

        if not file_hash:
            # Pokud 'file_hash' chybí, zaloguj to nebo nastav výchozí hodnotu
            file_hash = str(uuid.uuid4())  # Nebo jiná logika pro generování výchozího hash
            document['metadata']['file_hash'] = file_hash  # Přidej 'file_hash' do dokumentu

        # Vloží nebo aktualizuje dokument s podmínkou na file_hash
        collection.replace_one({"metadata.file_hash": file_hash}, document, upsert=True)

    def search_document_by_id(self, collection_name, document_id):
        collection = self.get_collection(collection_name)
        result = collection.find_one({"_id": document_id})
        if result:
            result["_id"] = str(result["_id"])  # Convert ObjectId to string
        return result

    def update_document(self, collection_name, query, update):
        collection = self.get_collection(collection_name)
        return collection.update_one(query, {"$set": update})

    def delete_documents(self, collection_name, query):
        collection = self.get_collection(collection_name)
        return collection.delete_many(query)

    def create_text_index(self, collection_name, field_name):
        collection = self.get_collection(collection_name)
        collection.create_index([(field_name, "text")])

    def search_documents(self, collection_name, query, n_results=1):
        collection = self.get_collection(collection_name)

        # Pokud je query typu ObjectId nebo string, pokusíme se vyhledat podle _id
        if isinstance(query, str) or isinstance(query, ObjectId):
            result = self.search_document_by_id(collection_name, query)
            if result:
                return [result]

        # Jinak vyhledáváme pomocí textového dotazu
        results = collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(n_results)

        # Convert ObjectId to string
        results = [{**doc, "_id": str(doc["_id"])} for doc in results]

        return list(results)

    def load_localization(self):
        collection = self.get_collection('localization')
        localization = collection.find_one({})
        if not localization:
            with open('settings/localization.json', 'r', encoding='utf-8') as f:
                localization = json.load(f)
            collection.insert_one(localization)
        return localization

    def get_translation(self, key, lang):
        localization = self.load_localization()
        return localization[lang][key]

    def update_localization(self, new_localization):
        collection = self.get_collection('localization')
        collection.replace_one({}, new_localization, upsert=True)

    def close_connection(self):
        self.client.close()

    def reload_localization(self):
        with open('settings/localization.json', 'r', encoding='utf-8') as f:
            localization = json.load(f)
        self.update_localization(localization)

    def clear_all_data(self):
        collections = self.db.list_collection_names()
        for collection_name in collections:
            self.db.drop_collection(collection_name)
            logger.log_warning(f"Dropped collection: {collection_name}")
            print(f"Dropped collection: {collection_name}")

from elasticsearch import Elasticsearch
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
from celery import Celery
import os

# Elasticsearch setup
es = Elasticsearch([os.getenv("ES_HOST", "http://localhost:9200")])

# Celery setup
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    'indexer_node',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Preprocessing function
def preprocess_content(content):
    # Tokenize the content (split into words)
    tokens = word_tokenize(content.lower())
    # Remove stopwords
    stop_words = set(stopwords.words("english"))
    filtered_tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
    # Apply stemming
    stemmer = PorterStemmer()
    stemmed_tokens = [stemmer.stem(word) for word in filtered_tokens]
    # Join tokens back into a single string
    return " ".join(stemmed_tokens)

@celery_app.task(name='indexer_node.index_content_task', queue='ingest_tasks')
def index_content_task(data):
    """
    Celery task to preprocess and index content into Elasticsearch.
    Expects data to be a dict with 'content' and 'meta_data'.
    """
    try:
        content = data.get("content", "")
        meta_data = data.get("meta_data", {})
        preprocessed = preprocess_content(content)
        doc = {
            "content": preprocessed,
            "meta_data": meta_data
        }
        doc_id = meta_data.get("url")
        resp = es.index(index="my_index", id=doc_id, document=doc, refresh=True)
        return {"status": "indexed", "id": resp["_id"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}
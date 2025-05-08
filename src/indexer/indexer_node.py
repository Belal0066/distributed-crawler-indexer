from elasticsearch import Elasticsearch
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk


es = Elasticsearch(["http://localhost:9200"])

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

try:
    # Force refresh immediately after indexing
    document = [
        # Web Development
        {
            "content": "Introduction to React hooks and functional components in modern web development.",
            "meta_data": {"author": "Dev Team", "url": "https://example.com/react-hooks", "timestamp": "2025-03-15", "category": "frontend"}
        },
        {
            "content": "How to optimize Django queries for better database performance in Python web apps.",
            "meta_data": {"author": "Python Weekly", "url": "https://example.com/django-optimization", "timestamp": "2025-04-10", "category": "backend"}
        },
        
        # AI/ML
        {
            "content": "Transformer architectures revolutionized NLP with models like BERT and GPT-3.",
            "meta_data": {"author": "AI Research Lab", "url": "https://example.com/transformers", "timestamp": "2025-01-22", "category": "ai"}
        },
        {
            "content": "Practical guide to implementing computer vision with TensorFlow 2.0 and OpenCV.",
            "meta_data": {"author": "ML Engineer", "url": "https://example.com/computer-vision", "timestamp": "2025-04-18", "category": "ai"}
        },
        
        # Databases
        {
            "content": "Comparing NoSQL databases: MongoDB vs Cassandra for high-throughput applications.",
            "meta_data": {"author": "DB Admin", "url": "https://example.com/nosql-comparison", "timestamp": "2025-02-28", "category": "database"}
        },
        {
            "content": "PostgreSQL 15 introduces new JSON functions and improved indexing capabilities.",
            "meta_data": {"author": "Database Weekly", "url": "https://example.com/postgresql-15", "timestamp": "2025-04-05", "category": "database"}
        },
        
        # DevOps
        {
            "content": "Kubernetes networking explained: Pods, Services, and Ingress controllers.",
            "meta_data": {"author": "DevOps Engineer", "url": "https://example.com/k8s-networking", "timestamp": "2025-03-30", "category": "devops"}
        },
        {
            "content": "CI/CD pipelines with GitHub Actions: From commit to production deployment.",
            "meta_data": {"author": "DevOps Team", "url": "https://example.com/github-actions", "timestamp": "2025-04-12", "category": "devops"}
        },
        
        # Cybersecurity
        {
            "content": "OWASP Top 10 vulnerabilities every web developer should know in 2025.",
            "meta_data": {"author": "Security Expert", "url": "https://example.com/owasp-2025", "timestamp": "2025-04-01", "category": "security"}
        },
        {
            "content": "Implementing zero-trust architecture for microservices environments.",
            "meta_data": {"author": "CISO", "url": "https://example.com/zero-trust", "timestamp": "2025-03-25", "category": "security"}
        },
        
        # Additional Varied Content
        {
            "content": "The evolution of JavaScript: ES2025 features with practical examples.",
            "meta_data": {"author": "JS Developer", "url": "https://example.com/es2025", "timestamp": "2025-04-20", "category": "frontend"}
        },
        {
            "content": "Building real-time dashboards with FastAPI and WebSockets.",
            "meta_data": {"author": "Fullstack Dev", "url": "https://example.com/fastapi-websockets", "timestamp": "2025-04-15", "category": "fullstack"}
        },
        {
            "content": "Machine learning model deployment patterns: Batch vs real-time inference.",
            "meta_data": {"author": "MLOps Engineer", "url": "https://example.com/ml-deployment", "timestamp": "2025-04-08", "category": "ai"}
        },
        {
            "content": "Automating infrastructure provisioning with Terraform and AWS CDK.",
            "meta_data": {"author": "Cloud Architect", "url": "https://example.com/terraform-cdk", "timestamp": "2025-03-18", "category": "devops"}
        },
        {
            "content": "Analyzing 1M+ product reviews with Elasticsearch aggregations.",
            "meta_data": {"author": "Data Analyst", "url": "https://example.com/es-aggregations", "timestamp": "2025-04-22", "category": "database"}
        },
        {
            "content": "Migrating from monolithic architecture to microservices: Lessons learned.",
            "meta_data": {"author": "CTO", "url": "https://example.com/microservices-migration", "timestamp": "2025-02-10", "category": "architecture"}
        },
        {
            "content": "Practical TypeScript: Advanced type system features for enterprise apps.",
            "meta_data": {"author": "TS Expert", "url": "https://example.com/advanced-typescript", "timestamp": "2025-04-17", "category": "frontend"}
        },
        {
            "content": "Serverless cost optimization: Cold starts vs provisioned concurrency.",
            "meta_data": {"author": "Cloud Economist", "url": "https://example.com/serverless-costs", "timestamp": "2025-03-05", "category": "cloud"}
        },
        {
            "content": "Building accessible web components with WAI-ARIA and React.",
            "meta_data": {"author": "UX Engineer", "url": "https://example.com/accessible-components", "timestamp": "2025-04-19", "category": "frontend"}
        },
        {
            "content": "Blue-green deployments with Kubernetes and Istio service mesh.",
            "meta_data": {"author": "SRE", "url": "https://example.com/blue-green-k8s", "timestamp": "2025-03-22", "category": "devops"}
        },
        {
            "content": "Understanding CAP theorem in distributed databases: A practical approach.",
            "meta_data": {"author": "DBA", "url": "https://example.com/cap-theorem", "timestamp": "2025-04-11", "category": "database"}
        },
        {
            "content": "Implementing OAuth 2.0 and OpenID Connect for secure API access.",
            "meta_data": {"author": "Security Architect", "url": "https://example.com/oauth-openid", "timestamp": "2025-03-28", "category": "security"}
        },
        {
            "content": "GraphQL vs REST: Choosing the right API architecture for your application.",
            "meta_data": {"author": "API Designer", "url": "https://example.com/graphql-vs-rest", "timestamp": "2025-04-14", "category": "api"}
        }
    ]
    # Index each document individually with a unique ID (e.g., the URL)
    for doc in document:
        # Preprocess the content field
        doc["content"] = preprocess_content(doc["content"])
        # Use the URL as the unique ID
        doc_id = doc["meta_data"]["url"]
        resp = es.index(index="my_index", id=doc_id, document=doc, refresh=True)
        print(f"Indexed document with ID: {resp['_id']}")
    
    # Print preprocessing results
    print("Preprocessed documents:")
    for doc in document:
        print(f"ID: {doc['meta_data']['url']}, Content: {doc['content']}")

    # Prompt the user for input
    search_query = input("Enter your search query: ").strip()
    search_type = input("Enter search type (match, phrase, boolean): ").strip().lower()

    # Build the query dynamically based on user input
    if search_type == "phrase":
        # Phrase search with fuzziness
        query = {
            "query": {
                "match_phrase": {
                    "content": {
                        "query": search_query,
                        "slop": 2  # Allows for slight word reordering
                    }
                }
            }
        }
    elif search_type == "boolean":
        # Boolean search with fuzziness
        must_query = input("Enter 'must' query (required terms): ").strip()
        must_not_query = input("Enter 'must_not' query (excluded terms): ").strip()
        should_query = input("Enter 'should' query (preferred terms): ").strip()

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"content": {"query": must_query, "fuzziness": "AUTO"}}}
                    ],
                    "must_not": [
                        {"match": {"content": {"query": must_not_query, "fuzziness": "AUTO"}}}
                    ],
                    "should": [
                        {"match": {"content": {"query": should_query, "fuzziness": "AUTO"}}}
                    ]
                }
            }
        }
    else:
        # Default to match query with fuzziness
        query = {
            "query": {
                "match": {
                    "content": {
                        "query": search_query,
                        "fuzziness": "AUTO"
                    }
                }
            }
        }

    # Execute the search query
    try:
        response = es.search(index="my_index", body=query)
        print(f"Found {response['hits']['total']['value']} results:")
        for hit in response['hits']['hits']:
            print(hit['_source'])
    except Exception as e:
        print(f"Error: {str(e)}")

except Exception as e:
    print(f"Error: {str(e)}")
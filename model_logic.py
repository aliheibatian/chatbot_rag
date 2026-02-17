
import os
import time
import uuid
import numpy as np
import datetime
import unicodedata
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Dict, Tuple, Optional, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from sentence_transformers import CrossEncoder
from FlagEmbedding import BGEM3FlagModel
from pymilvus import AnnSearchRequest, WeightedRanker, connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from scipy.sparse import csr_matrix
import re
from thefuzz import process, fuzz
import jdatetime

# --- Constants ---
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
KNOWLEDGE_COLLECTION_NAME = "llm_knowledge_base"
CONVERSATIONS_COLLECTION_NAME = "llm_conversations_history"
ADMIN_LIKED_COLLECTION_NAME = "admin_liked_interactions"
MONGO_URI = 'mongodb://localhost:27017/'
CACHE_SEARCH_K = 10
RETRIEVED_DOCS_DIR = "/home/ali/Project/chatbot_rag/retrieved_docs"
NUM_FINAL_DOCS = 10
BGE_M3_MODEL_PATH = "/home/ali/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"
RERANKER_MODEL_PATH = "/home/ali/.cache/huggingface/hub/models--jinaai--jina-reranker-v2-base-multilingual"
DENSE_DIM = 1024
MATCH_CONFIDENCE_THRESHOLD = 60
CITATION_PATTERN = r'\[Source:\s*[\d\s,]+\]'
SUGGESTION_LIMIT = 5

# --- Check and create retrieved_docs directory ---
print("Checking retrieved_docs directory started")
if not os.path.exists(RETRIEVED_DOCS_DIR):
    os.makedirs(RETRIEVED_DOCS_DIR)
print("Checking retrieved_docs directory completed")

# --- Load Reranker model ---
print("Loading reranker model started")
try:
    reranker_model = CrossEncoder(RERANKER_MODEL_PATH, max_length=512, device='cpu', trust_remote_code=True)
    print("Loading reranker model completed")
except Exception as e:
    print(f"Error loading reranker: {e}")
    reranker_model = None

# --- Advanced question cleaning function ---
def clean_question(question: str) -> str:
    print("Cleaning question started")
    cleaned = ' '.join(question.strip().split())
    cleaned = unicodedata.normalize('NFKC', cleaned).replace('\u200c', ' ')
    cleaned = ' '.join(cleaned.split())
    print("Cleaning question completed")
    return cleaned

# --- Offline embedding function ---
class LocalBGEM3EmbeddingFunction:
    def __init__(self, model, use_fp16=False, device="cpu"):
        print("Initializing embedding function started")
        self.model = model
        self.device = device
        self.use_fp16 = use_fp16
        self.dim = {"dense": DENSE_DIM, "sparse": 100000}
        print("Initializing embedding function completed")

    def __call__(self, texts):
        print("Generating embeddings started")
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                max_length=8192,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )
            sparse_embeddings = []
            for sparse_dict in embeddings.get("lexical_weights", []):
                indices = list(sparse_dict.keys())
                values = list(sparse_dict.values())
                sparse_matrix = csr_matrix(
                    (np.array(values, dtype=np.float32), indices, [0, len(indices)]),
                    shape=(1, self.dim["sparse"])
                )
                sparse_embeddings.append(sparse_matrix)
            print("Generating embeddings completed")
            return {
                "dense": np.array(embeddings["dense_vecs"], dtype=np.float32),
                "sparse": sparse_embeddings[0] if sparse_embeddings else csr_matrix((1, self.dim["sparse"]), dtype=np.float32)
            }
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return {"dense": None, "sparse": None}
        








# --- New function for intelligent autocomplete ---
def find_similar_liked_questions(partial_question: str, admin_liked_collection: Any, ef: Any) -> List[Dict[str, Any]]:
    print("Finding similar admin-liked questions started")
    try:
        if not partial_question.strip():
            return []

        cleaned_question = clean_question(partial_question)
        query_embeddings = ef([cleaned_question])
        if query_embeddings["dense"] is None or query_embeddings["sparse"] is None:
            print("Embedding error for partial question.")
            return []

        query_dense_embedding = query_embeddings["dense"][0]
        query_sparse_embedding = query_embeddings["sparse"].getrow(0)
        
        dense_search_params = {"metric_type": "IP", "params": {}}
        sparse_search_params = {"metric_type": "IP", "params": {}}
        rerank = WeightedRanker(1.0, 1.0)
        
        dense_req = AnnSearchRequest(
            [query_dense_embedding], "dense_vector", dense_search_params, limit=5
        )
        sparse_req = AnnSearchRequest(
            [query_sparse_embedding], "sparse_vector", sparse_search_params, limit=5
        )
        
        results = admin_liked_collection.hybrid_search(
            [sparse_req, dense_req], rerank=rerank, limit=5, output_fields=["pk", "text"]
        )[0]
        
        similar_questions = []
        for hit in results:
            question_text = hit.get("text", "").strip()
            print(f"Found question: {question_text}, ID: {hit.get('pk')}, Score: {hit.score}")  # لاگ برای دیباگ
            similar_questions.append({
                "id": hit.get("pk"),
                "question": question_text,
                "score": hit.score
            })
            
        print("Finding similar admin-liked questions completed")
        return similar_questions
    except Exception as e:
        print(f"Error finding similar questions: {e}")
        return []

# --- New function to retrieve answer from cache ---
def get_answer_from_admin_cache(doc_id: str, admin_collection: Any) -> Optional[Dict[str, Any]]:
    print(f"Retrieving answer from admin cache for ID: {doc_id}")
    try:
        interaction = admin_collection.find_one({'_id': ObjectId(doc_id)})
        if interaction:
            print("Answer retrieved successfully from admin cache.")
            return {
                "answer": interaction.get('llm_answer'),
                "sources_data": interaction.get('sources_data', []),
                "source": "admin_cache_hit"
            }
        else:
            print(f"No document found with ID: {doc_id}")
            return None
    except Exception as e:
        print(f"Error retrieving answer from admin cache: {e}")
        return None
    











# --- Process and extract sources ---
def process_and_extract_sources(raw_answer: str, doc_sources_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    print("Processing sources started")
    final_sources_to_return = []
    if re.search(CITATION_PATTERN, raw_answer):
        source_map = {s['id']: s for s in doc_sources_data}
        processed_ids = set()
        pattern = r'([^.!?\n]+(?:[.!?]\s*)?\[Source:\s*([\d\s,]+)\])'
        matches = re.findall(pattern, raw_answer)
        for match in matches:
            generated_sentence = match[0].strip().replace('[Source:', '')
            source_ids = [int(s.strip()) for s in match[1].split(',')]
            for sid in source_ids:
                if sid in source_map:
                    source_detail = source_map[sid]
                    source_content = source_detail.get('content', '')
                    potential_lines = list(set([line.strip() for line in re.split(r'(?<=[.!?])\s+', source_content.replace('\n', ' ')) + source_content.split('\n') if line.strip()]))
                    if potential_lines:
                        best_match = process.extractOne(generated_sentence, potential_lines, scorer=fuzz.partial_ratio)
                        if best_match and best_match[1] > MATCH_CONFIDENCE_THRESHOLD:
                            source_detail.setdefault('quotes', []).append(best_match[0])
                    if sid not in processed_ids:
                        final_sources_to_return.append(source_detail)
                        processed_ids.add(sid)
    else:
        if doc_sources_data:
            choices = {doc['id']: doc['content'] for doc in doc_sources_data}
            best_doc_match = process.extractOne(raw_answer, choices, scorer=fuzz.token_set_ratio)
            if best_doc_match:
                best_doc_id = best_doc_match[2]
                for source_detail in doc_sources_data:
                    if source_detail['id'] == best_doc_id:
                        source_content = source_detail.get('content', '')
                        potential_lines = list(set([line.strip() for line in re.split(r'(?<=[.!?])\s+', source_content.replace('\n', ' ')) + source_content.split('\n') if line.strip()]))
                        if potential_lines:
                            best_quote_match = process.extractOne(raw_answer, potential_lines, scorer=fuzz.token_set_ratio)
                            if best_quote_match and best_quote_match[1] > 65:
                                source_detail.setdefault('quotes', []).append(best_quote_match[0])
                        final_sources_to_return.append(source_detail)
                        break
    print("Processing sources completed")
    return final_sources_to_return

# --- MongoDB connections ---
def get_mongo_collection() -> Optional[Any]:
    print("Connecting to MongoDB interactions started")
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client['llm_project_db']
        collection = db['interactions']
        print("Connecting to MongoDB interactions completed")
        return collection
    except Exception as e:
        print(f"Error connecting to MongoDB interactions: {e}")
        return None

def get_admin_mongo_collection() -> Optional[Any]:
    print("Connecting to MongoDB admin collection started")
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client['llm_project_db']
        collection = db['admin_liked_interactions']
        print("Connecting to MongoDB admin collection completed")
        return collection
    except Exception as e:
        print(f"Error connecting to MongoDB admin collection: {e}")
        return None

# --- Initialize Milvus and MongoDB ---
def get_milvus_retrievers_and_mongo_collections() -> Tuple[Any, Any, Any, Any, Any]:
    print("Initializing Milvus and MongoDB started")
    try:
        model = BGEM3FlagModel(model_name_or_path=BGE_M3_MODEL_PATH)
        ef = LocalBGEM3EmbeddingFunction(model=model, use_fp16=False, device="cpu")
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT, alias="default")
        
        if not utility.has_collection(CONVERSATIONS_COLLECTION_NAME):
            fields = [
                FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=100),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65534),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
                FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=DENSE_DIM),
            ]
            schema = CollectionSchema(fields, description="Conversation History")
            conversation_collection = Collection(CONVERSATIONS_COLLECTION_NAME, schema, consistency_level="Bounded")
            sparse_index = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}
            conversation_collection.create_index("sparse_vector", sparse_index)
            dense_index = {"index_type": "AUTOINDEX", "metric_type": "IP"}
            conversation_collection.create_index("dense_vector", dense_index)
            conversation_collection.load()
        else:
            conversation_collection = Collection(CONVERSATIONS_COLLECTION_NAME)
            conversation_collection.load()
        
        # Initialize admin_liked_interactions collection in Milvus
        if not utility.has_collection(ADMIN_LIKED_COLLECTION_NAME):
            fields = [
                FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=100),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65534),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
                FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=DENSE_DIM),
            ]
            schema = CollectionSchema(fields, description="Admin Liked Interactions")
            admin_liked_collection = Collection(ADMIN_LIKED_COLLECTION_NAME, schema, consistency_level="Bounded")
            sparse_index = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}
            admin_liked_collection.create_index("sparse_vector", sparse_index)
            dense_index = {"index_type": "AUTOINDEX", "metric_type": "IP"}
            admin_liked_collection.create_index("dense_vector", dense_index)
            admin_liked_collection.load()
        else:
            admin_liked_collection = Collection(ADMIN_LIKED_COLLECTION_NAME)
            admin_liked_collection.load()
        
        mongo_collection = get_mongo_collection()
        admin_collection = get_admin_mongo_collection()

        admin_collection.create_index([("user_question", 1), ("liked_by_admin", 1), ("start_date", 1), ("end_date", 1)])
        print("Initializing Milvus and MongoDB completed")
        return Collection(KNOWLEDGE_COLLECTION_NAME), conversation_collection, mongo_collection, admin_collection, ef, admin_liked_collection
    except Exception as e:
        print(f"Error initializing Milvus and MongoDB: {e}")
        return None, None, None, None, None, None

# --- Sync admin_liked_interactions to Milvus ---
def sync_admin_liked_to_milvus(admin_collection: Any, admin_liked_collection: Any, ef: Any):
    print("Syncing admin liked interactions to Milvus started")
    try:
        admin_docs = admin_collection.find({"liked_by_admin": True})
        existing_ids = set()
        for hit in admin_liked_collection.query(expr="", output_fields=["pk"], limit=1000):
            existing_ids.add(hit["pk"])
        
        for doc in admin_docs:
            doc_id = str(doc["_id"])
            if doc_id not in existing_ids:
                question = clean_question(doc["user_question"])
                embeddings = ef([question])
                if embeddings["dense"] is None or embeddings["sparse"] is None:
                    print(f"Embedding error for question: {question}")
                    continue
                sparse_dict = {int(idx): float(val) for idx, val in zip(embeddings["sparse"].indices, embeddings["sparse"].data) if idx < embeddings["sparse"].shape[1]}
                entities = [
                    [doc_id],
                    [question],
                    ["admin_liked"],
                    [sparse_dict],
                    [embeddings["dense"][0]]
                ]
                admin_liked_collection.insert(entities)
        print("Syncing admin liked interactions to Milvus completed")
    except Exception as e:
        print(f"Error syncing admin liked interactions: {e}")

# --- Clear rated interactions ---
def clear_rated_interactions(mongo_collection: Any, conversation_vectorstore: Any) -> None:
    print("Clearing rated interactions started")
    try:
        if mongo_collection is None:
            print("No MongoDB connection")
            return
        
        rated_interactions = mongo_collection.find({
            "like_status": {"$in": ["like", "dislike"]}
        })
        
        for interaction in rated_interactions:
            interaction_id = str(interaction["_id"])
            conversation_vectorstore.delete(expr=f"pk == '{interaction_id}'")
        
        mongo_collection.delete_many({
            "like_status": {"$in": ["like", "dislike"]}
        })
        print("Clearing rated interactions completed")
    except Exception as e:
        print(f"Error clearing rated interactions: {e}")

# --- Save admin-liked interaction ---
def save_admin_liked_interaction(interaction_id: str, mongo_collection: Any, admin_collection: Any, admin_liked_collection: Any, ef: Any, start_date: str, end_date: str) -> bool:
    print("Saving admin-liked interaction started")
    try:
        interaction_id_obj = ObjectId(interaction_id)
        interaction = mongo_collection.find_one({'_id': interaction_id_obj})
        if not interaction:
            print(f"Interaction {interaction_id} not found")
            return False
        
        cleaned_question = clean_question(interaction['question'])
        existing_doc = admin_collection.find_one({"user_question": cleaned_question, "liked_by_admin": True})
        if existing_doc:
            print(f"Document already exists for question: {cleaned_question}")
            return True
        
        doc_id = str(ObjectId())
        admin_collection.insert_one({
            "_id": ObjectId(doc_id),
            "user_question": cleaned_question,
            "llm_answer": interaction['answer'],
            "start_date": start_date,
            "end_date": end_date if end_date else "بدون انقضا",
            "liked_by_admin": True,
            "timestamp": time.time(),
            "sources_data": interaction.get("sources_data", [])
        })

        # Add to admin_liked_collection in Milvus
        embeddings = ef([cleaned_question])
        if embeddings["dense"] is None or embeddings["sparse"] is None:
            print(f"Embedding error for admin liked interaction: {cleaned_question}")
            return False
        sparse_dict = {int(idx): float(val) for idx, val in zip(embeddings["sparse"].indices, embeddings["sparse"].data) if idx < embeddings["sparse"].shape[1]}
        entities = [
            [doc_id],
            [cleaned_question],
            ["admin_liked"],
            [sparse_dict],
            [embeddings["dense"][0]]
        ]
        admin_liked_collection.insert(entities)
        print("Saving admin-liked interaction completed")
        return True
    except Exception as e:
        print(f"Error saving admin-liked interaction: {e}")
        return False

# --- Check cache ---
def check_cache(question: str, mongo_collection: Any, admin_collection: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    print("Checking cache started")
    try:
        if mongo_collection is None or admin_collection is None:
            print("No MongoDB connection")
            return None, None, "error"
        
        cleaned_question = clean_question(question)
        now_jalali_str = jdatetime.datetime.now().strftime('%Y-%m-%d')
        
        query = {
            "user_question": cleaned_question,
            "start_date": {"$lte": now_jalali_str},
            "$or": [
                {"end_date": {"$gte": now_jalali_str}},
                {"end_date": "بدون انقضا"}
            ],
            "liked_by_admin": True
        }
        admin_cache_result = admin_collection.find_one(query)
        if admin_cache_result:
            print("Cache hit in admin collection")
            return admin_cache_result["llm_answer"], str(admin_cache_result["_id"]), "admin_cache_hit"

        user_query = {
            "question": cleaned_question,
            "like_status": "like"
        }
        user_cache_result = mongo_collection.find_one(user_query)
        if user_cache_result:
            print("Cache hit in user collection")
            return user_cache_result["answer"], str(user_cache_result["_id"]), "user_cache_hit"

        print("No cache hit")
        return None, None, None
    except Exception as e:
        print(f"Cache check error: {e}")
        return None, None, "error"

# --- Update conversation cache ---
def update_conversation_cache(interaction_id: str, like_status: str, mongo_collection: Any, conversation_vectorstore: Any, admin_liked_collection: Any, ef: Any, question: Optional[str] = None, ollama_client: Optional[Any] = None, knowledge_collection: Optional[Any] = None, admin_collection: Optional[Any] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    print("Updating conversation cache started")
    try:
        interaction_id_obj = ObjectId(interaction_id)
        mongo_collection.update_one({'_id': interaction_id_obj}, {'$set': {'like_status': like_status}})
        
        if like_status == "dislike":
            conversation_vectorstore.delete(expr=f"pk == '{interaction_id}'")
            if question and ollama_client and knowledge_collection and conversation_vectorstore and ef:
                new_answer, new_interaction_id, source, _ = ask_llm(
                    question, [], ollama_client, mongo_collection, admin_collection, knowledge_collection, conversation_vectorstore, ef, admin_liked_collection
                )
                print("Updating conversation cache completed")
                return True, new_answer, new_interaction_id
        
        if like_status == "like":
            interaction = mongo_collection.find_one({'_id': interaction_id_obj})
            if interaction:
                text = f"Question: {interaction['question']}\nAnswer: {interaction['answer']}"
                source = "cached_conversation"
                dense_vector = interaction["question_embedding_dense"]
                sparse_data = interaction["question_embedding_sparse"]
                sparse_dict = {int(idx): float(val) for idx, val in zip(sparse_data["indices"], sparse_data["data"]) if idx < sparse_data["shape"]}
                
                entities = [
                    [str(interaction_id)],
                    [text],
                    [source],
                    [sparse_dict],
                    [dense_vector]
                ]
                conversation_vectorstore.insert(entities)
                
                if admin_collection and start_date:
                    save_admin_liked_interaction(interaction_id, mongo_collection, admin_collection, admin_liked_collection, ef, start_date, end_date)
        
        print("Updating conversation cache completed")
        return True, None, None
    except Exception as e:
        print(f"Cache update error: {e}")
        return False, None, None

# --- Save retrieved documents ---
def save_retrieved_docs_to_file(docs: List[Document], question: str, filename_prefix: str, scores: Optional[List[float]] = None):
    print("Saving retrieved documents started")
    try:
        unique_filename = f"{filename_prefix}_{uuid.uuid4()}.txt"
        with open(os.path.join(RETRIEVED_DOCS_DIR, unique_filename), "w", encoding="utf-8") as f:
            f.write(f"--- User Question ---\n")
            f.write(f"{question}\n\n")
            
            if scores:
                f.write(f"--- Documents with {filename_prefix} Scores ---\n\n")
                for i, (doc, score) in enumerate(zip(docs, scores)):
                    f.write(f"### Document #{i+1} (Score: {score:.6f})\n")
                    f.write(doc.page_content + "\n")
                    f.write(f"Source: {doc.metadata.get('source', 'Unknown')}\n")
                    f.write("\n")
            else:
                f.write("--- Selected Final Documents ---\n\n")
                for i, doc in enumerate(docs):
                    f.write(f"### Document #{i+1}\n")
                    f.write(doc.page_content + "\n")
                    f.write(f"Source: {doc.metadata.get('source', 'Unknown')}\n")
                    f.write("\n")
        print(f"Saving retrieved documents completed: {unique_filename}")
    except Exception as e:
        print(f"Error saving documents: {e}")

# --- Main LLM function ---
def ask_llm(question: str, history: List[Dict[str, str]], ollama_client: Any, mongo_collection: Any, admin_collection: Any, knowledge_collection: Any, conversation_vectorstore: Any, ef: Any, admin_liked_collection: Any) -> Tuple[str, Optional[str], str, List[Dict[str, Any]]]:
    print("Processing LLM request started")
    if knowledge_collection is None or conversation_vectorstore is None or mongo_collection is None or admin_collection is None or admin_liked_collection is None:
        print("Database connection error")
        return "Service unavailable due to database connection error", None, "error", []
    
    cached_answer, cached_id, source = check_cache(question, mongo_collection, admin_collection)
    if cached_answer:
        print("Processing LLM request completed with cache hit")
        return cached_answer, cached_id, source, []

    query_embeddings = ef([question])
    if query_embeddings["dense"] is None or query_embeddings["sparse"] is None:
        print("Query embedding error")
        return "Error generating question embedding", None, "error", []
    
    query_dense_embedding = query_embeddings["dense"][0]
    query_sparse_embedding = query_embeddings["sparse"].getrow(0)

    try:
        class GraphState(TypedDict):
            question: str
            context: List[Document]
            context_str: str
            doc_sources_data: List[Dict]
            answer: str
            source: str
            final_sources: List[Dict]

        def retrieve(state: GraphState):
            print("Retrieve node started")
            question = state['question']
            query_embeddings = ef([question])
            if query_embeddings["dense"] is None or query_embeddings["sparse"] is None:
                print("Embedding error in retrieve")
                return {"context": [], "doc_sources_data": [], "context_str": ""}
            
            query_dense_embedding = query_embeddings["dense"][0]
            query_sparse_embedding = query_embeddings["sparse"].getrow(0)
            dense_search_params = {"metric_type": "IP", "params": {}}
            sparse_search_params = {"metric_type": "IP", "params": {}}
            rerank = WeightedRanker(1.0, 1.0)
            
            dense_req = AnnSearchRequest(
                [query_dense_embedding], "dense_vector", dense_search_params, limit=15
            )
            sparse_req = AnnSearchRequest(
                [query_sparse_embedding], "sparse_vector", sparse_search_params, limit=15
            )
            res_knowledge = knowledge_collection.hybrid_search(
                [sparse_req, dense_req], rerank=rerank, limit=15, output_fields=["text", "source"]
            )[0]
            
            initial_retrieved_docs_knowledge = []
            initial_scores_knowledge = []
            for hit in res_knowledge:
                doc = Document(page_content=hit.get("text"), metadata={"source": hit.get("source")})
                initial_retrieved_docs_knowledge.append(doc)
                initial_scores_knowledge.append(hit.score)
            
            save_retrieved_docs_to_file(initial_retrieved_docs_knowledge, question, "hybrid_search_knowledge_results", initial_scores_knowledge)

            dense_req_conv = AnnSearchRequest(
                [query_dense_embedding], "dense_vector", dense_search_params, limit=15
            )
            sparse_req_conv = AnnSearchRequest(
                [query_sparse_embedding], "sparse_vector", sparse_search_params, limit=15
            )
            res_conversation = conversation_vectorstore.hybrid_search(
                [sparse_req_conv, dense_req_conv], rerank=rerank, limit=15, output_fields=["text", "source"]
            )[0]
            
            initial_retrieved_docs_conversation = []
            initial_scores_conversation = []
            for hit in res_conversation:
                doc = Document(page_content=hit.get("text"), metadata={"source": hit.get("source")})
                initial_retrieved_docs_conversation.append(doc)
                initial_scores_conversation.append(hit.score)
            
            save_retrieved_docs_to_file(initial_retrieved_docs_conversation, question, "hybrid_search_conversation_results", initial_scores_conversation)

            final_retrieved_docs = initial_retrieved_docs_knowledge[:5] + initial_retrieved_docs_conversation[:2]

            if reranker_model:
                pairs = [[question, doc.page_content] for doc in final_retrieved_docs]
                try:
                    rerank_scores = reranker_model.predict(pairs, batch_size=16)
                except Exception as e:
                    print(f"Reranking error: {e}")
                    rerank_scores = [0.0] * len(pairs)
                
                reranked_docs_with_scores = sorted(zip(final_retrieved_docs, rerank_scores), key=lambda x: x[1], reverse=True)
                final_retrieved_docs = [doc for doc, score in reranked_docs_with_scores[:NUM_FINAL_DOCS * 2]]
                reranked_scores = [score for doc, score in reranked_docs_with_scores[:NUM_FINAL_DOCS * 2]]
                save_retrieved_docs_to_file(final_retrieved_docs, question, "reranked_results", reranked_scores)

            context_parts = []
            doc_sources_data = []
            for i, doc in enumerate(final_retrieved_docs, 1):
                metadata = doc.metadata or {}
                filename = metadata.get("source", "Unknown")
                context_parts.append(f"[Source: {i}]\nFile: {filename}\nContent:\n{doc.page_content}")
                doc_sources_data.append({
                    "id": i,
                    "filename": filename,
                    "content": doc.page_content
                })
            context = "\n\n---\n\n".join(context_parts)
            
            save_retrieved_docs_to_file(final_retrieved_docs, question, "final_selected_docs")
            print("Retrieve node completed")
            return {"context": final_retrieved_docs, "doc_sources_data": doc_sources_data, "context_str": context}

        def generate(state: GraphState):
            print("Generate node started")
            context = state["context_str"]
            system_prompt =  """شما یک دستیار هوشمند و متخصص در حوزه برق و انشعابات هستید. وظیفه شما پاسخ دادن به سؤالات کاربران به زبان فارسی، با لحنی دوستانه و محاوره‌ای است، اما دقت و صحت اطلاعات در اولویت شما قرار دارد.

دستورالعمل‌های کلیدی:
1.  **پاسخ دقیق**: پاسخ شما باید کاملاً بر اساس اطلاعاتی باشد که در "زمینه" (context) ارائه شده.
2.  **درک عددی**: باید قادر به درک و مقایسه اعداد باشید. برای مثال، اگر در متن "بیش از 25 کیلووات" ذکر شده و سؤال در مورد "26 کیلووات" است، باید متوجه شوید که این دو با هم همخوانی دارند.
3.  **ترکیب اطلاعات**: اگر برای یک سؤال چندین داکیومنت در "زمینه" وجود دارد، اطلاعات را با هم ترکیب کرده و یک پاسخ جامع و کامل ارائه دهید.
4.  **مدیریت مکالمه**: اگر یکی از داکیومنت‌ها حاوی یک مکالمه (پرسش و پاسخ) است، از آن به عنوان یک نمونه برای درک بهتر موضوع استفاده کنید، اما پاسخ نهایی خود را بر اساس **تمام اطلاعات موجود در "زمینه"** شکل دهید. یعنی صرفاً به آن مکالمه اکتفا نکنید و بقیه داکیومنت‌ها را نیز در نظر بگیرید.
5.  **صداقت در پاسخ**: اگر اطلاعات کافی برای پاسخ به یک سؤال مشخص وجود ندارد، به هیچ وجه حدس و گمان نزنید. به جای آن، به کاربر محترمانه و به صورت واضح بگویید: "ببخشید، من اطلاعات کافی برای پاسخ به این سؤال رو ندارم."
6.  **لحن و فرمت**: پاسخ‌ها باید مختصر، مفید و با لحن محاوره‌ای و دوستانه باشند. از کلمات یا اصطلاحات دشوار و غیرضروری پرهیز کنید.

زمینه:
{context}

سؤال کاربر:
{question}

پاسخ:
                    """

            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{question}")
            ])
            
            messages = prompt_template.invoke({
                "question": state['question'],
                "context": context
            })
            
            llm = OllamaLLM(model="llama3.1:8b", temperature=0.3)
            raw_answer = llm.invoke(messages).strip()
            doc_sources_data = state["doc_sources_data"]
            final_sources = process_and_extract_sources(raw_answer, doc_sources_data)
            source = "rag_langgraph_generation"
            print("Generate node completed")
            return {"answer": raw_answer, "source": source, "final_sources": final_sources}

        workflow = StateGraph(GraphState)
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("generate", generate)
        
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        
        graph = workflow.compile()
        initial_state = {"question": question, "context": [], "context_str": "", "doc_sources_data": [], "answer": "", "source": "", "final_sources": []}
        final_state = graph.invoke(initial_state)

        generated_answer = final_state['answer']
        source_info = final_state['source']
        final_sources_to_return = final_state['final_sources']
        interaction_id = str(ObjectId())

        query_sparse_data = query_sparse_embedding.data.tolist()
        query_sparse_indices = query_sparse_embedding.indices.tolist()
        query_sparse_indptr = query_sparse_embedding.indptr.tolist()
        query_sparse_shape = query_sparse_embedding.shape[1]

        mongo_collection.insert_one({
            "_id": ObjectId(interaction_id),
            "question": clean_question(question),
            "answer": generated_answer,
            "source": source_info,
            "timestamp": time.time(),
            "like_status": "unrated",
            "question_embedding_dense": query_dense_embedding.tolist(),
            "question_embedding_sparse": {
                "data": query_sparse_data,
                "indices": query_sparse_indices,
                "indptr": query_sparse_indptr,
                "shape": query_sparse_shape
            },
            "sources_data": final_sources_to_return
        })
        print("Processing LLM request completed")
        return generated_answer, interaction_id, source_info, final_sources_to_return
    except Exception as e:
        print(f"RAG process error: {e}")
        return "System error, please try again later", None, "error", []
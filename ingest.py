import os
import glob
import numpy as np
from pymilvus import utility, connections, Collection, FieldSchema, CollectionSchema, DataType
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from FlagEmbedding import BGEM3FlagModel
import nltk
from typing import List
from pymongo import MongoClient  # اضافه‌شده برای MongoDB

# --- ثابت‌ها ---
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
KNOWLEDGE_COLLECTION_NAME = "llm_knowledge_base"
DATA_DIRECTORY = "/home/ali/Project/chatbot_rag/data"
BGE_M3_MODEL_PATH = "/home/ali/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"
DENSE_DIM = 1024
MONGO_URI = 'mongodb://localhost:27017/'  # اضافه‌شده

# --- ۱. بارگذاری مدل Embedding ---
print("در حال بارگذاری مدل Embedding (BGE-M3) از مسیر محلی...")
try:
    model = BGEM3FlagModel(model_name_or_path=BGE_M3_MODEL_PATH)

    class MilvusBGEM3EmbeddingFunction:
        def __init__(self, model):
            self.model = model

        def __call__(self, texts: List[str]):
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                max_length=8192,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )
            dense_vecs = np.array(embeddings["dense_vecs"], dtype=np.float32)
            return {
                "dense": dense_vecs,
                "sparse": embeddings.get("lexical_weights", {})
            }

    milvus_ef = MilvusBGEM3EmbeddingFunction(model=model)
    print("✅ مدل BGE-M3 با موفقیت از مسیر محلی بارگذاری شد.")
except Exception as e:
    print(f"❌ خطا در بارگذاری مدل Milvus BGEM3 از مسیر محلی: {e}")
    exit()

# --- ۲. بارگذاری و تقسیم‌بندی اسناد ---
print("در حال بارگذاری و تقسیم‌بندی اسناد با رویکرد RecursiveCharacterTextSplitter...")
all_splits = []
filepaths = glob.glob(os.path.join(DATA_DIRECTORY, "**/*.txt"), recursive=True)

if not filepaths:
    print(f"❌ هیچ فایل .txt در پوشه {DATA_DIRECTORY} یافت نشد.")
    exit()

try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    print("داده‌های nltk punkt یافت نشد، در حال دانلود...")
    nltk.download('punkt')

def get_chunks_from_text(document_text, source_path):
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", r"\d+-\d+", r"\d+\.\d+"],
        chunk_size=1000,
        chunk_overlap=200,
        keep_separator=True
    )
    
    chunks = text_splitter.split_text(document_text)
    
    return [
        {
            "text": chunk,
            "source": source_path
        }
        for chunk in chunks
    ]

for filepath in filepaths:
    try:
        loader = TextLoader(filepath, encoding='utf-8')
        docs = loader.load()
        document_text = docs[0].page_content
        source_path = os.path.basename(filepath)
        
        chunks = get_chunks_from_text(document_text, source_path)
        
        for chunk in chunks:
            all_splits.append({
                "page_content": chunk["text"],
                "metadata": {"source": chunk["source"]}
            })
        print(f"✅ فایل {source_path} با موفقیت به {len(chunks)} قطعه تقسیم شد.")
    except Exception as e:
        print(f"خطا در خواندن یا پردازش فایل {filepath}: {e}")

if not all_splits:
    print("❌ هیچ سندی برای پردازش وجود ندارد. برنامه متوقف می‌شود.")
    exit()

print(f"✅ در مجموع {len(all_splits)} قطعه متن از {len(filepaths)} فایل ایجاد شد.")

# --- ۳. آماده‌سازی Milvus و ذخیره‌سازی دانش ---
print("در حال آماده‌سازی دیتابیس وکتوری Milvus...")
try:
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    if utility.has_collection(KNOWLEDGE_COLLECTION_NAME):
        print(f"کالکشن قدیمی '{KNOWLEDGE_COLLECTION_NAME}' یافت شد. در حال حذف آن...")
        utility.drop_collection(KNOWLEDGE_COLLECTION_NAME)

    fields = [
        FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, auto_id=True, max_length=100),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65534),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
        FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=DENSE_DIM),
    ]
    schema = CollectionSchema(fields, description="Knowledge Base for Hybrid Search")
    knowledge_collection = Collection(KNOWLEDGE_COLLECTION_NAME, schema, consistency_level="Bounded")

    sparse_index = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}
    knowledge_collection.create_index("sparse_vector", sparse_index)
    dense_index = {"index_type": "AUTOINDEX", "metric_type": "IP"}
    knowledge_collection.create_index("dense_vector", dense_index)
    knowledge_collection.load()

    print("در حال تولید بردارهای دوگانه و ذخیره‌سازی در Milvus...")

    texts_to_insert = [doc["page_content"] for doc in all_splits]
    metadatas_to_insert = [doc["metadata"] for doc in all_splits]

    embeddings = milvus_ef(texts_to_insert)

    entities = [
        texts_to_insert,
        [m.get("source", "نامشخص") for m in metadatas_to_insert],
        embeddings["sparse"],
        embeddings["dense"],
    ]

    knowledge_collection.insert(entities)
    knowledge_collection.flush()
    print(f"✅ {knowledge_collection.num_entities} سند با موفقیت در '{KNOWLEDGE_COLLECTION_NAME}' ذخیره شد.")

    # --- پاک کردن داده‌های مکالمات از Milvus ---
    conv_col_name = "admin_liked_interactions"
    if utility.has_collection(conv_col_name):
        conv_col = Collection(conv_col_name)
        conv_col.delete(expr="pk like '%'")
        conv_col.flush()
        print(f"✅ تمام داده‌های '{conv_col_name}' از Milvus پاک شد (تعداد موجودیت‌های باقی‌مانده: {conv_col.num_entities}).")

    # --- پاک کردن داده‌ها از MongoDB ---
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['llm_project_db']
    db['interactions'].delete_many({})
    db['admin_liked_interactions'].delete_many({})
    print("✅ تمام داده‌ها از کالکشن‌های 'interactions' و 'admin_liked_interactions' در MongoDB پاک شد.")

except Exception as e:
    print(f"❌ خطا در هنگام کار با Milvus یا MongoDB: {e}")
    raise
finally:
    if "default" in connections.list_connections():
        connections.disconnect("default")






# from pymilvus import connections, Collection, utility
# connections.connect(host='localhost', port='19530')
# print(utility.list_collections())  # Lists collections (tables)



# from pymilvus import connections, Collection, utility

# # اتصال به Milvus
# connections.connect(host='localhost', port='19530')

# # لیست کالکشن‌ها
# collections = ['admin_liked_interactions', 'llm_conversations_history']

# # بررسی داده‌های هر کالکشن
# for coll_name in collections:
#     print(f"\nCollection: {coll_name}")
#     coll = Collection(coll_name)
#     coll.load()  # لود کردن کالکشن
#     try:
#         results = coll.query(expr='pk != ""', output_fields=['pk', 'text', 'source'], limit=100)  # بدون بردارها
#         if results:
#             print(f"Data in {coll_name}:")
#             for result in results:
#                 print(result)
#         else:
#             print(f"No data found in {coll_name}")
#     except Exception as e:
#         print(f"Error in {coll_name}: {e}")





# from pymilvus import connections, Collection, utility

# # Connecting to Milvus server
# connections.connect(host="localhost", port="19530")

# # Specifying the collection to delete
# collection_name = "llm_conversations_history,admin_liked_interactions"

# # Checking if collection exists and dropping it
# if utility.has_collection(collection_name):
#     collection = Collection(collection_name)
#     collection.drop()
#     print(f"Collection {collection_name} has been deleted.")
# else:
#     print(f"Collection {collection_name} does not exist.")
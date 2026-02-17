# RAG Chatbot

Intelligent Persian-language chatbot using **Retrieval-Augmented Generation (RAG)** to answer questions based on custom documents (e.g. city regulations, laws, FAQs).

[chatbot_rag.webm](https://github.com/user-attachments/assets/335ad57d-c6df-4825-934e-232b21568ad0)


## Features
- Persian document ingestion & chunking
- Vector search with embedding model
- Context-aware generation using LLM
- **Hybrid + semantic search on previous questions & answers liked by admin**  
  As you type, it searches similar past questions semantically/hybrid → shows quick matches → click to instantly get the answer (no need to query sources again)
- Streamlit frontend
- Modular architecture

[answer_by_adminlike.webm](https://github.com/user-attachments/assets/1908b358-3023-4528-af98-a17185dfc255)

## Tech Stack
- Python 3.10+
- LangChain / Langgraph 
- Embeddings: BGE-M3
- Reranker: jina reranker multilingual
- LLM:Llama3.1:8b
- Vector store: Milvus
- UI: Streamlit

## Quick Start

1. Clone repo
```bash
git clone https://github.com/aliheibatian/chatbot_rag.git
cd chatbot_rag

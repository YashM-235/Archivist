<div align="center">
  
<img src="https://capsule-render.vercel.app/api?type=venom&color=0:0d0d0d,30:2d0b0b,60:7f1d1d,100:dc2626&height=220&section=header&text=Archivist&fontSize=82&fontColor=ff6b6b&fontAlignY=55&animation=twinkling&stroke=ffe5e5&strokeWidth=2&desc=Ask%20your%20documents%20anything%20-%20grounded,%20cited,%20and%20yours.&descSize=18&descAlignY=75&descColor=ffffff"/>

An enterprise-grade Retrieval-Augmented Generation (RAG) system for querying your own PDFs-books, novels, research papers, manuals, reports, or policy documents-in natural language, with every answer grounded in retrieved context and traced back to the exact page it came from.

Runs locally: your documents stay on your machine. Only the user query and the retrieved document excerpts are sent to the LLM for answer generation.

<p align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-black.svg)](https://flask.palletsprojects.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B.svg)](https://streamlit.io/)
[![FAISS](https://img.shields.io/badge/Vector%20Search-FAISS-005571.svg)](https://github.com/facebookresearch/faiss)
[![Groq](https://img.shields.io/badge/Inference-Groq%20API-F55036.svg)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

</p>
</div>
---

## Why Archivist

Traditional chatbots answer from what they already "know," making it difficult to verify whether an answer actually comes from your documents.

Archivist generates answers **only** from retrieved content in your uploaded PDFs and provides page-level citations for every response, making verification simple.

Think of it as **NotebookLM for your own infrastructure**-self-hosted, provider-agnostic, and built to be extended.

---

## ✨ Features

- Query any PDF in natural language
- Semantic search using Sentence Transformers
- Page-level citations
- Multi-document support
- Conversational follow-ups
- Flask and Streamlit front ends sharing one FAISS index
- Local embeddings for privacy
- Robust PDF parsing with graceful fallback handling

---

## 🧠 How it works

```mermaid
flowchart LR
A[PDF Upload] --> B[Chunking]
B --> C[Embeddings]
C --> D[(FAISS)]
E[User Query] --> F[Query Embedding]
F --> D
D --> G[Relevant Chunks]
G --> H[Groq LLM]
H --> I[Answer + Citations]
```

### Mapping to the RAG Pipeline

| Step | Implementation |
|------|----------------|
| Document Processing | `modules/document_processor.py` extracts text page-by-page and creates overlapping sentence-aware chunks. |
| Embeddings | `modules/vector_store.py` creates Sentence Transformer embeddings and stores them in FAISS. |
| Retrieval | Semantic cosine similarity search over indexed chunks. |
| Generation | `modules/llm_client.py` injects retrieved context into the LLM prompt and produces grounded answers with citations. |

---

## 🖥️ Two Front Ends

### Flask

```bash
python app.py
```

### Streamlit

```bash
streamlit run streamlit_app.py
```

Both interfaces share the same vector database.

---

## 🚀 Quick Start

```bash
git clone https://github.com/<your-username>/archivist.git
cd archivist

python -m venv venv
# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

Download a free Groq API key from https://console.groq.com/keys

```bash
export GROQ_API_KEY="gsk_..."
# Windows
set GROQ_API_KEY=gsk_...
```

Run:

```bash
python app.py
```
or

```bash
streamlit run streamlit_app.py
```

---

## 📁 Project Structure

```text
archivist/
├── app.py
├── streamlit_app.py
├── config.py
├── modules/
│   ├── document_processor.py
│   ├── vector_store.py
│   └── llm_client.py
├── templates/
├── static/
├── data/
└── requirements.txt
```

---

## ⚙️ Design Choices

- Local Sentence Transformer embeddings keep documents private.
- FAISS `IndexFlatIP` provides exact cosine similarity search.
- Every response is freshly grounded in retrieved chunks.
- Shared persistent vector index for both UIs.
- OCR can be added later for scanned PDFs.

---

## 🛠️ Tech Stack

| Layer | Technology |
|------|------------|
| PDF Parsing | PyMuPDF, pypdf |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector Search | FAISS |
| LLM | Groq API |
| Backend | Python(3.11) , Flask |
| Frontend | Flask + Vanilla JS, Streamlit |

---

## 🗺️ Roadmap

- Provider-agnostic LLM support
- Local inference
- Hybrid search
- Cross-encoder reranking
- OCR support
- Pinecone / Qdrant integration
- Authentication
- Multi-user support
- Streaming responses
- Analytics dashboard

---
## 📸 Outputs

### 🏠 1. Home Interface

*Initial landing page showcasing the chat interface, document library, and sidebar.*

<p align="center">
  <img src="https://github.com/user-attachments/assets/b1b3f3c3-acaf-44ea-a76c-21e09ae19cb3"
       alt="Home Interface"
       width="900">
</p>

---

### 📄 2. Uploading Documents

*Uploading one or more PDF documents to build the knowledge base.*

<p align="center">
  <img src="https://github.com/user-attachments/assets/7e6621d0-2908-4d2f-8709-7a11e6dc28aa"
       alt="Uploading Documents"
       width="900">
</p>

---

### ⚙️ 3. Document Indexing

*Documents successfully processed into sentence-aware chunks, embedded, and stored in the FAISS vector database.*

<p align="center">
  <img src="https://github.com/user-attachments/assets/c3c1eb80-6ff4-49e4-bd7e-cb8d2413d183"
       alt="Document Indexing"
       width="900">
</p>

---

### 💬 4. Querying Documents & AI-Generated Response

*Users can ask natural language questions about their uploaded documents. Archivist retrieves the most relevant passages from the FAISS vector store and generates a grounded response using the Groq LLM, complete with page-level citations for verification.*

<p align="center">
  <img src="https://github.com/user-attachments/assets/566598a3-8c0e-491f-831c-f594aee180e2"
       alt="Asking a Question"
       width="900">
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/e24ab714-4b24-45a6-a468-7fb69a1d6457"
       alt="Uploading Documents"
       width="900">
</p>

---
## 🤝 Contributing

Issues and pull requests are welcome.

---

## 📄 License

MIT License.

---

<p align="center">
<sub>Built as part of a final-year project.</sub>
</p>

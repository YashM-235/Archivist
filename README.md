# Archive — Enterprise RAG System

An internal, NotebookLM-style chatbot for querying your own PDFs (books, novels, reports,
policy docs, whatever) with grounded, cited answers. Runs locally — your documents never
leave your machine except for the final question + retrieved excerpts sent to Groq for
answer generation.

## How it maps to the RAG pipeline

| Step | Where |
|---|---|
| 1. Break documents into sections | `modules/document_processor.py` — extracts text per PDF page, splits into overlapping, sentence-aware chunks |
| 2. Convert text into embeddings + store in a vector DB | `modules/vector_store.py` — `sentence-transformers` (local, free) embeddings written to a FAISS index, persisted to disk |
| 3. Retrieve relevant sections for a query | `VectorStore.search()` — cosine similarity search, optionally filtered to a subset of documents |
| 4. Generate grounded answers | `modules/llm_client.py` — calls the Groq API with the retrieved excerpts injected into the prompt, and instructs the model to cite `[doc, page]` for every claim |

`app.py` is the Flask server wiring these together behind a small REST API and a dark,
"reading room" themed single-page UI (`templates/index.html`, `static/`).

## Two front ends, same pipeline

- **Flask** (`app.py` + `templates/` + `static/`): REST API + hand-built dark UI.
- **Streamlit** (`streamlit_app.py`): same four modules underneath, run with:
  ```bash
  streamlit run streamlit_app.py
  ```
  Faster to iterate on, native `st.chat_message`/`st.chat_input`, and markdown renders
  correctly out of the box. Both share the same `data/vector_store/` index, so documents
  you add through one show up in the other.

## Setup

```bash
cd enterprise-rag
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

First run downloads the embedding model (`all-MiniLM-L6-v2`, ~90MB) from Hugging Face —
needs internet access once, then it's cached locally.

Get a Groq API key from [console.groq.com](https://console.groq.com/keys). You can either:

- Set it as an environment variable so you don't have to paste it every session:
  ```bash
  export GROQ_API_KEY="gsk_..."      # Windows: set GROQ_API_KEY=gsk_...
  ```
- Or just paste it into the "Groq API key" field in the UI — it's sent per-request and
  never written to disk.

## Run

```bash
python3 app.py
```

Open `http://localhost:5000`. Add PDFs from the sidebar, wait for indexing to finish, then
ask questions in the chat box. Uncheck documents in the sidebar to scope a question to a
subset of your shelf.

## Notes on the model choice

Groq deprecated `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` in mid-2026. This
project defaults to `openai/gpt-oss-120b` with `openai/gpt-oss-20b` (fastest) and
`qwen/qwen3.6-27b` (strongest reasoning) as alternatives in the model dropdown. Groq's
lineup changes fairly often — if you pick this project back up later, double check
[console.groq.com/docs/models](https://console.groq.com/docs/models) before assuming these
are still current.

## Design choices worth knowing about

- **Local embeddings, not Groq/OpenAI embeddings**: Groq doesn't currently offer an
  embeddings endpoint, so this uses `sentence-transformers` running on CPU. It's free,
  keeps your document content from ever being sent anywhere during indexing, and is more
  than accurate enough for this scale of corpus.
- **FAISS `IndexFlatIP`**: exact (not approximate) cosine similarity search. Perfectly fast
  for anything up to a few hundred thousand chunks — a few dozen books' worth of text.
  If you outgrow that, swap in `IndexIVFFlat` or a managed vector DB (Pinecone, Qdrant,
  Weaviate) behind the same `VectorStore` interface.
- **No delete-by-id**: FAISS's flat index doesn't support deleting individual vectors, so
  removing a document rebuilds the index from the remaining chunks. Fine for internal-tool
  scale; would need a different vector DB if documents churn constantly at large scale.
- **Chat continuity**: the last few turns are replayed to Groq on each question so
  follow-ups ("what about the sequel?") retain context, but every answer is still
  re-grounded in freshly retrieved chunks rather than relying on the model's memory of the
  conversation.
- **Scanned/image-only PDFs**: `pypdf` only extracts text that's already selectable text in
  the PDF. If you need OCR for scanned books, add a pre-processing step with
  `pytesseract` or similar before `process_pdf()`.
- **Answer formatting**: the system prompt (`modules/llm_client.py`) explicitly asks the
  model for plain, conversational prose instead of bold headers/nested bullets, and tells
  it not to write inline `[Source: ...]` citations since the UI already shows a real,
  retrieval-grounded source list under every answer. In the Flask UI, answers are rendered
  through `marked.js` + `DOMPurify` (see `static/js/script.js`) so markdown actually renders
  instead of showing literal `**`/`*` characters; Streamlit renders markdown natively via
  `st.markdown`, so no extra step was needed there.

## Project layout

```
enterprise-rag/
├── app.py                       # Flask routes
├── config.py                    # chunk size, models, paths
├── modules/
│   ├── document_processor.py    # PDF → chunks
│   ├── vector_store.py          # embeddings + FAISS
│   └── llm_client.py            # Groq prompt + call
├── templates/index.html
├── static/css/style.css
├── static/js/script.js
├── data/uploads/                # saved PDFs (gitignored)
└── data/vector_store/           # FAISS index + metadata (gitignored)
```

## Extending it

- **Auth**: this has none — it's meant to sit behind your existing internal-tool auth
  (VPN, SSO proxy, etc.), not to be exposed publicly.
- **Multi-user isolation**: right now the FAISS index is shared across everyone hitting the
  server. For per-team or per-user shelves, namespace the `doc_id` metadata and always pass
  `doc_ids` on search, or spin up a separate `VectorStore` per tenant.
- **Streaming answers**: `Groq`'s SDK supports `stream=True`; swap `llm_client.answer_query`
  to yield chunks and adjust the `/api/ask` route to a streaming response if you want
  token-by-token output in the UI.

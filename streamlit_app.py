"""
Streamlit front end for Archive — same four-step RAG pipeline as app.py (Flask), just a
different UI on top of the same modules/document_processor.py, modules/vector_store.py,
and modules/llm_client.py.

Run with: streamlit run streamlit_app.py
"""

import os
import uuid

import streamlit as st

import config
from modules.document_processor import process_pdf
from modules.vector_store import VectorStore
from modules.llm_client import answer_query

st.set_page_config(page_title="Archive — Document Q&A", page_icon="📚", layout="wide")


# ---------- cached heavy resources (survive reruns; shared across sessions) ----------

@st.cache_resource(show_spinner="Loading embedding model…")
def get_store():
    return VectorStore()


store = get_store()


# ---------- per-session state ----------

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role", "content", "sources"}]
if "indexed_hashes" not in st.session_state:
    st.session_state.indexed_hashes = set()
if "doc_selection" not in st.session_state:
    st.session_state.doc_selection = {}  # doc_id -> bool (checked/unchecked)


# ---------- sidebar: the stacks ----------

with st.sidebar:
    st.markdown("## 📚 Archive")
    st.caption("internal document Q&A")

    api_key = st.text_input("Groq API key", type="password", placeholder="gsk_...",
                             value=os.environ.get(config.GROQ_API_KEY_ENV, ""))
    model_ids = [m["id"] for m in config.AVAILABLE_MODELS]
    model_labels = {m["id"]: m["label"] for m in config.AVAILABLE_MODELS}
    model = st.selectbox("Model", options=model_ids, format_func=lambda mid: model_labels[mid])

    st.divider()
    st.markdown("### Shelf")

    uploaded_files = st.file_uploader(
        "Add PDF(s)", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed"
    )

    if uploaded_files:
        for f in uploaded_files:
            file_key = f"{f.name}-{f.size}"
            if file_key in st.session_state.indexed_hashes:
                continue  # already processed this exact file this session

            with st.spinner(f"Indexing {f.name}…"):
                doc_id = str(uuid.uuid4())
                save_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}.pdf")
                with open(save_path, "wb") as out:
                    out.write(f.getbuffer())

                try:
                    records = process_pdf(
                        save_path, doc_id, f.name,
                        chunk_size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP
                    )
                    if not records:
                        st.error(f"No extractable text found in {f.name}. Scanned/image-only PDF?")
                        os.remove(save_path)
                    else:
                        store.add_records(records)
                        st.session_state.doc_selection[doc_id] = True
                        st.success(f"Added {f.name} ({len(records)} sections indexed).")
                except Exception as e:
                    st.error(f"Failed to process {f.name}: {e}")

            st.session_state.indexed_hashes.add(file_key)

    documents = store.list_documents()
    if not documents:
        st.caption("No documents yet. Add a PDF to start querying it.")
    else:
        for doc in documents:
            doc_id = doc["doc_id"]
            st.session_state.doc_selection.setdefault(doc_id, True)

            row = st.columns([5, 1])
            with row[0]:
                st.session_state.doc_selection[doc_id] = st.checkbox(
                    f"{doc['doc_name']}  ·  {doc['chunks']} sections",
                    value=st.session_state.doc_selection[doc_id],
                    key=f"chk_{doc_id}",
                )
            with row[1]:
                if st.button("🗑", key=f"del_{doc_id}", help="Remove from shelf"):
                    store.delete_document(doc_id)
                    st.session_state.doc_selection.pop(doc_id, None)
                    st.rerun()


# ---------- main: reading room ----------

st.markdown("### Ask your documents anything")
st.caption("Every answer is grounded only in what's on the shelf, with sources shown below it.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            src_line = "  ·  ".join(f"📄 {s['doc_name']} (p.{s['page_num']})" for s in msg["sources"])
            st.caption(src_line)

query = st.chat_input("Ask a question about the documents on your shelf…")

if query:
    if not api_key:
        st.error("Enter your Groq API key in the sidebar first.")
    else:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        selected_doc_ids = [d for d, v in st.session_state.doc_selection.items() if v] or None

        with st.chat_message("assistant"):
            with st.spinner("Searching the shelf…"):
                chunks = store.search(query, top_k=config.TOP_K, doc_ids=selected_doc_ids)

            sources = []
            if not chunks:
                answer = "No relevant content found. Upload documents first, or try rephrasing your question."
            else:
                # last few turns for continuity, excluding the user message just appended above
                chat_history_for_llm = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1][-6:]
                ]
                try:
                    with st.spinner("Thinking…"):
                        answer = answer_query(api_key, model, query, chunks, chat_history_for_llm)
                    sources = [
                        {"doc_name": c["doc_name"], "page_num": c["page_num"], "score": round(c["score"], 3)}
                        for c in chunks
                    ]
                except Exception as e:
                    answer = f"Groq API error: {e}"

            st.markdown(answer)
            if sources:
                src_line = "  ·  ".join(f"📄 {s['doc_name']} (p.{s['page_num']})" for s in sources)
                st.caption(src_line)

        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})

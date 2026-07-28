import os
import uuid
import logging

from flask import Flask, request, jsonify, render_template

import config
from modules.document_processor import process_pdf
from modules.vector_store import VectorStore
from modules.llm_client import answer_query

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# Vector store is built once at startup and shared across requests/threads.
store = VectorStore()


@app.route("/")
def index():
    return render_template("index.html",
                            documents=store.list_documents(),
                            models=config.AVAILABLE_MODELS,
                            default_model=config.GROQ_MODEL)


@app.route("/api/documents", methods=["GET"])
def get_documents():
    return jsonify(store.list_documents())


@app.route("/api/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a PDF file."}), 400

    doc_id = str(uuid.uuid4())
    filename = file.filename
    save_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}.pdf")
    file.save(save_path)

    try:
        records = process_pdf(save_path, doc_id, filename,
                               chunk_size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP)
        if not records:
            os.remove(save_path)
            return jsonify({"error": "No extractable text found. Is this a scanned/image-only PDF?"}), 400
        store.add_records(records)
    except Exception as e:
        app.logger.exception("Failed to process upload for %s", filename)
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500

    return jsonify({"doc_id": doc_id, "doc_name": filename, "chunks_indexed": len(records)})


@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    store.delete_document(doc_id)
    upload_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}.pdf")
    if os.path.exists(upload_path):
        os.remove(upload_path)
    return jsonify({"status": "deleted"})


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    api_key = data.get("api_key") or os.environ.get(config.GROQ_API_KEY_ENV)
    model = data.get("model") or config.GROQ_MODEL
    doc_ids = data.get("doc_ids") or None  # None/empty = search across all documents
    chat_history = data.get("chat_history") or []

    if not query:
        return jsonify({"error": "Query cannot be empty."}), 400
    if not api_key:
        return jsonify({"error": "A Groq API key is required. Enter it in the field above."}), 400

    chunks = store.search(query, top_k=config.TOP_K, doc_ids=doc_ids)
    if not chunks:
        return jsonify({
            "answer": "No relevant content found. Upload documents first, or try rephrasing your question.",
            "sources": []
        })

    try:
        answer = answer_query(api_key, model, query, chunks, chat_history)
    except Exception as e:
        return jsonify({"error": f"Groq API error: {str(e)}"}), 500

    sources = [
        {"doc_name": c["doc_name"], "page_num": c["page_num"], "score": round(c["score"], 3)}
        for c in chunks
    ]
    return jsonify({"answer": answer, "sources": sources})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

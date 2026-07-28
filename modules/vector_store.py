"""
Steps 2 & 3 of the RAG pipeline:
  - Convert chunk text into embeddings (sentence-transformers, runs locally/free)
  - Store embeddings in a vector database (FAISS) and persist to disk
  - Retrieve the most relevant chunks for a given query
"""

import os
import pickle
import faiss
from sentence_transformers import SentenceTransformer

import config


class VectorStore:
    def __init__(self, model_name=config.EMBEDDING_MODEL, index_dir=config.INDEX_DIR):
        self.model = SentenceTransformer(model_name)
        self.index_dir = index_dir
        self.dim = self.model.get_sentence_embedding_dimension()
        self.index_path = os.path.join(index_dir, "index.faiss")
        self.meta_path = os.path.join(index_dir, "metadata.pkl")
        self.index = None
        self.metadata = []  # list parallel to vectors in self.index
        self._load()

    # ---------- persistence ----------

    def _load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            self.index = faiss.IndexFlatIP(self.dim)  # inner product on normalized vecs = cosine sim
            self.metadata = []

    def _save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.metadata, f)

    # ---------- embedding ----------

    def _embed(self, texts):
        vecs = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        faiss.normalize_L2(vecs)
        return vecs.astype("float32")

    # ---------- writes ----------

    def add_records(self, records):
        """records: list of dicts, each must have a 'text' field plus any metadata."""
        if not records:
            return
        vecs = self._embed([r["text"] for r in records])
        self.index.add(vecs)
        self.metadata.extend(records)
        self._save()

    def delete_document(self, doc_id):
        """
        FAISS's flat index has no native delete-by-id, so we rebuild the index
        excluding the target document. Fine for the moderate corpus sizes an
        internal tool like this deals with.
        """
        keep = [r for r in self.metadata if r["doc_id"] != doc_id]
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata = []
        if keep:
            self.add_records(keep)
        else:
            self._save()

    # ---------- reads ----------

    def search(self, query, top_k=config.TOP_K, doc_ids=None):
        """Return top_k most relevant chunks, optionally restricted to a set of doc_ids."""
        if self.index.ntotal == 0:
            return []
        qvec = self._embed([query])
        k = min(top_k * 5, self.index.ntotal) if doc_ids else min(top_k, self.index.ntotal)
        scores, indices = self.index.search(qvec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            record = self.metadata[idx]
            if doc_ids and record["doc_id"] not in doc_ids:
                continue
            results.append({**record, "score": float(score)})
            if len(results) >= top_k:
                break
        return results

    def list_documents(self):
        docs = {}
        for r in self.metadata:
            docs.setdefault(r["doc_id"], {"doc_id": r["doc_id"], "doc_name": r["doc_name"], "chunks": 0})
            docs[r["doc_id"]]["chunks"] += 1
        return list(docs.values())

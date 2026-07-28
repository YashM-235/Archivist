"""
Step 4 of the RAG pipeline: use a language model (via Groq API) to generate
answers grounded strictly in the retrieved content, with source citations.
"""

from groq import Groq

SYSTEM_PROMPT = """You are an internal enterprise document assistant. Answer the user's \
question using ONLY the information in the provided context excerpts below.

Write like you're explaining this to a colleague in a message: plain sentences and natural \
paragraphs. Only reach for a bulleted list when you're genuinely listing several distinct \
items - not as a container for a single explanation. Don't use bold section headers or \
nested bullets; that reads like a formatted report, not an answer.

Do not add inline citations like "[Source: ...]" in your answer. The interface already \
shows exactly which document and page each excerpt came from, right below your answer, so \
just answer directly and naturally.

If the context doesn't contain enough information to answer, say so plainly rather than \
guessing or filling gaps with outside knowledge.
"""


def build_context_block(chunks):
    blocks = [f"[{c['doc_name']}, page {c['page_num']}]\n{c['text']}" for c in chunks]
    return "\n\n---\n\n".join(blocks)


def answer_query(api_key, model, query, chunks, chat_history=None):
    """
    api_key: Groq API key (user-supplied, never stored server-side)
    model: Groq model id, e.g. "openai/gpt-oss-120b"
    query: the user's question
    chunks: retrieved chunk records from VectorStore.search()
    chat_history: optional list of {"role": "user"/"assistant", "content": str} for continuity
    """
    client = Groq(api_key=api_key)
    context_block = build_context_block(chunks)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if chat_history:
        messages.extend(chat_history[-6:])  # keep last few turns only

    user_content = f"Context excerpts:\n\n{context_block}\n\nQuestion: {query}"
    messages.append({"role": "user", "content": user_content})

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=1024,
    )
    return completion.choices[0].message.content

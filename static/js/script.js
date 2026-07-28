const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const docList = document.getElementById('docList');
const emptyHint = document.getElementById('emptyHint');
const chatScroll = document.getElementById('chatScroll');
const composerForm = document.getElementById('composerForm');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const apiKeyInput = document.getElementById('apiKey');
const modelSelect = document.getElementById('modelSelect');

let chatHistory = []; // {role, content} pairs sent to the LLM for continuity

// persist the API key only in-memory for this tab session (not localStorage,
// so it never lingers on a shared machine)
queryInput.addEventListener('input', () => {
  queryInput.style.height = 'auto';
  queryInput.style.height = Math.min(queryInput.scrollHeight, 160) + 'px';
});

// ---------- upload ----------

fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;

  uploadStatus.textContent = `Indexing ${file.name}…`;
  uploadStatus.className = 'upload-status';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      uploadStatus.textContent = data.error || 'Upload failed.';
      uploadStatus.className = 'upload-status error';
      return;
    }

    uploadStatus.textContent = `Added ${data.doc_name} (${data.chunks_indexed} sections indexed).`;
    uploadStatus.className = 'upload-status ok';
    addDocToList(data.doc_id, data.doc_name, data.chunks_indexed);
    emptyHint.style.display = 'none';
  } catch (err) {
    uploadStatus.textContent = 'Network error while uploading.';
    uploadStatus.className = 'upload-status error';
  } finally {
    fileInput.value = '';
  }
});

function addDocToList(docId, docName, chunkCount) {
  const li = document.createElement('li');
  li.className = 'doc-item';
  li.dataset.docId = docId;
  li.innerHTML = `
    <label>
      <input type="checkbox" class="doc-checkbox" checked value="${docId}">
      <span class="doc-name">${escapeHtml(docName)}</span>
    </label>
    <span class="doc-meta">${chunkCount} sections</span>
    <button class="doc-remove" title="Remove from shelf">&times;</button>
  `;
  docList.appendChild(li);
}

docList.addEventListener('click', async (e) => {
  if (!e.target.classList.contains('doc-remove')) return;
  const li = e.target.closest('.doc-item');
  const docId = li.dataset.docId;
  li.style.opacity = '0.4';
  try {
    await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
    li.remove();
    if (!docList.children.length) emptyHint.style.display = 'block';
  } catch (err) {
    li.style.opacity = '1';
  }
});

// ---------- chat ----------

composerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;

  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) {
    alert('Enter your Groq API key first.');
    apiKeyInput.focus();
    return;
  }

  const selectedDocIds = Array.from(document.querySelectorAll('.doc-checkbox:checked')).map(cb => cb.value);

  appendUserMessage(query);
  queryInput.value = '';
  queryInput.style.height = 'auto';
  sendBtn.disabled = true;

  const typingEl = appendTyping();

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        api_key: apiKey,
        model: modelSelect.value,
        doc_ids: selectedDocIds,
        chat_history: chatHistory
      })
    });
    const data = await res.json();
    typingEl.remove();

    if (!res.ok) {
      appendAssistantMessage(data.error || 'Something went wrong.', [], true);
      return;
    }

    appendAssistantMessage(data.answer, data.sources || []);
    chatHistory.push({ role: 'user', content: query });
    chatHistory.push({ role: 'assistant', content: data.answer });
  } catch (err) {
    typingEl.remove();
    appendAssistantMessage('Network error reaching the server.', [], true);
  } finally {
    sendBtn.disabled = false;
  }
});

function appendUserMessage(text) {
  const tpl = document.getElementById('tpl-user-msg').content.cloneNode(true);
  tpl.querySelector('.msg-bubble').textContent = text;
  chatScroll.appendChild(tpl);
  scrollToBottom();
}

function appendAssistantMessage(text, sources, isError = false) {
  const tpl = document.getElementById('tpl-assistant-msg').content.cloneNode(true);
  const bubble = tpl.querySelector('.msg-bubble');

  if (isError) {
    bubble.textContent = text;
    bubble.classList.add('error');
  } else {
    const rawHtml = marked.parse(text, { breaks: true });
    bubble.innerHTML = DOMPurify.sanitize(rawHtml);
  }

  const sourcesEl = tpl.querySelector('.sources');
  sources.forEach(s => {
    const card = document.getElementById('tpl-source-card').content.cloneNode(true);
    card.querySelector('.source-doc').textContent = s.doc_name;
    card.querySelector('.source-page').textContent = s.page_num;
    card.querySelector('.source-score').textContent = s.score;
    sourcesEl.appendChild(card);
  });

  chatScroll.appendChild(tpl);
  scrollToBottom();
}

function appendTyping() {
  const div = document.createElement('div');
  div.className = 'msg msg-assistant';
  div.innerHTML = '<div class="typing">searching the shelf…</div>';
  chatScroll.appendChild(div);
  scrollToBottom();
  return div;
}

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

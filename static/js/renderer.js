// ==================== 文件说明 ====================
// 这是前端渲染模块，负责 DOM 元素的创建和更新
//
// 本版关键变化：
// createMessageElement 若 msg 带 citations 字段，自动渲染引用块，
// 用于切换会话后恢复引用来源

import { $, isNearBottom, renderMarkdown } from './utils.js';
import { store } from './store.js';

// ==================== DOM 元素引用 ====================
export const elements = {
  messages: $('#messages'),
  historyList: $('#history-list'),
  chatTitle: $('#chat-header-title'),
  emptyState: $('#empty-state'),
  sendBtn: $('#send-btn'),
  uploadStatus: $('#upload-status-text'),
  uploadProgress: $('#upload-progress-bar'),
  scrollBottomBtn: $('#scroll-bottom-btn'),
  sidebar: $('#sidebar'),
  sidebarOverlay: $('#sidebar-overlay'),
};

let activePopup = null;

function closePopup() {
  if (activePopup) {
    activePopup.classList.remove('show');
    activePopup = null;
  }
}

function openPopup(popup) {
  closePopup();
  popup.classList.add('show');
  activePopup = popup;
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.popup-menu') && !e.target.closest('.item-menu-btn')) {
    closePopup();
  }
});

function handleHistoryClick(e) {
  const item = e.target.closest('.history-item');
  if (!item) return;
  if (e.target.closest('.item-menu-btn') || e.target.closest('.popup-menu')) return;

  store.switchTo(item.dataset.id);
  renderAll();
  if (window.innerWidth <= 768) closeSidebar();
  document.getElementById('user-input')?.focus();
}

function createHistoryItem(conv) {
  const item = document.createElement('div');
  item.className = `history-item ${conv.id === store.currentId ? 'active' : ''}`;
  item.setAttribute('role', 'listitem');
  item.tabIndex = 0;
  item.dataset.id = conv.id;

  const titleSpan = document.createElement('span');
  titleSpan.className = 'item-title';
  titleSpan.textContent = conv.title;
  titleSpan.title = conv.title;

  const menuBtn = document.createElement('button');
  menuBtn.className = 'item-menu-btn';
  menuBtn.innerHTML = '⋯';
  menuBtn.setAttribute('aria-label', '更多操作');
  menuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const popup = item.querySelector('.popup-menu');
    if (popup.classList.contains('show')) {
      closePopup();
    } else {
      openPopup(popup);
    }
  });

  const popup = document.createElement('div');
  popup.className = 'popup-menu';
  popup.innerHTML = `
    <div class="popup-menu-item rename-item">✏️ 重命名</div>
    <div class="popup-menu-item danger delete-item">🗑️ 删除</div>
  `;

  popup.querySelector('.rename-item').addEventListener('click', (e) => {
    e.stopPropagation();
    closePopup();
    const newTitle = prompt('请输入新标题', conv.title);
    if (newTitle && newTitle.trim()) {
      store.renameConversation(conv.id, newTitle.trim());
      renderAll();
    }
  });

  popup.querySelector('.delete-item').addEventListener('click', (e) => {
    e.stopPropagation();
    closePopup();
    store.deleteConversation(conv.id);
    renderAll();
  });

  item.appendChild(titleSpan);
  item.appendChild(menuBtn);
  item.appendChild(popup);

  return item;
}

export function renderAll() {
  renderHistory();
  renderMessages();
}

function renderHistory() {
  const list = elements.historyList;
  list.innerHTML = '';
  const sorted = Object.values(store.conversations).sort((a, b) => b.createdAt - a.createdAt);

  list.removeEventListener('click', handleHistoryClick);
  list.addEventListener('click', handleHistoryClick);

  sorted.forEach(conv => {
    list.appendChild(createHistoryItem(conv));
  });
}

function renderMessages() {
  const container = elements.messages;
  const conv = store.getCurrent();

  if (!conv || conv.messages.length === 0) {
    elements.emptyState.style.display = 'flex';
    container.querySelectorAll('.message').forEach(m => m.remove());
    container.appendChild(elements.emptyState);
    return;
  }

  elements.emptyState.style.display = 'none';
  container.innerHTML = '';
  container.appendChild(elements.emptyState);

  conv.messages.forEach(msg => {
    container.appendChild(createMessageElement(msg));
  });

  scrollToBottom();
}

export function createMessageElement(msg) {
  const div = document.createElement('div');
  div.className = `message ${msg.role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = msg.role === 'user' ? '👤' : '🤖';

  const content = document.createElement('div');
  content.className = 'message-content';
  content.innerHTML = renderMarkdown(msg.content);
  postRenderContent(content);

  div.appendChild(avatar);
  div.appendChild(content);

  // 若该消息已存有 citations（比如切回历史会话时），自动渲染
  if (msg.citations) {
    appendCitations(div, msg.citations);
  }

  return div;
}

export function appendMessage(role, content) {
  const msgEl = createMessageElement({ role, content });
  elements.messages.appendChild(msgEl);
  scrollToBottom();
  return msgEl;
}

export function updateMessageContent(element, content) {
  const contentEl = element.querySelector('.message-content');
  if (contentEl) {
    contentEl.classList.remove('streaming-text');
    contentEl.innerHTML = renderMarkdown(content);
    postRenderContent(contentEl);
  }
}

export function updateMessageText(element, text) {
  const contentEl = element.querySelector('.message-content');
  if (contentEl) {
    contentEl.classList.add('streaming-text');
    contentEl.textContent = text;
  }
}

export function finalizeMessageContent(element, text) {
  const contentEl = element.querySelector('.message-content');
  if (contentEl) {
    contentEl.classList.remove('streaming-text');
    contentEl.innerHTML = renderMarkdown(text);
    postRenderContent(contentEl);
  }
}

// ==================== 引用来源渲染 ====================
export function appendCitations(messageEl, citations) {
  if (!messageEl || !citations) return;

  const existing = messageEl.querySelector('.citations');
  if (existing) existing.remove();

  const keys = Object.keys(citations);
  if (!keys.length) return;

  const box = document.createElement('div');
  box.className = 'citations';

  const title = document.createElement('div');
  title.className = 'citations-title';
  title.textContent = '📚 参考来源';
  box.appendChild(title);

  const list = document.createElement('div');
  list.className = 'citations-list';

  keys.forEach((k) => {
    const c = citations[k] || {};
    const item = document.createElement('div');
    item.className = 'citation-item';

    const source = c.source || c.title || '未知来源';
    const page = c.page ? ` 第 ${c.page} 页` : '';

    const header = document.createElement('div');
    header.className = 'citation-header';
    const numSpan = document.createElement('strong');
    numSpan.textContent = `[${k}]`;
    header.appendChild(numSpan);
    header.appendChild(document.createTextNode(` ${source}${page}`));
    item.appendChild(header);

    const detail = document.createElement('div');
    detail.className = 'citation-detail';
    detail.textContent = c.text || '（无原文）';
    detail.style.display = 'none';
    item.appendChild(detail);

    item.addEventListener('click', () => {
      detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
    });

    list.appendChild(item);
  });

  box.appendChild(list);
  messageEl.appendChild(box);
}

// ==================== 后处理 ====================
function postRenderContent(container) {
  if (window.hljs) {
    container.querySelectorAll('pre code').forEach(block => {
      hljs.highlightElement(block);
      const pre = block.parentElement;
      if (!pre.querySelector('.copy-code-btn')) {
        const btn = document.createElement('button');
        btn.className = 'copy-code-btn';
        btn.textContent = '📋';
        btn.addEventListener('click', () => {
          navigator.clipboard.writeText(block.textContent).then(() => {
            btn.textContent = '✓';
            setTimeout(() => btn.textContent = '📋', 2000);
          });
        });
        pre.style.position = 'relative';
        pre.appendChild(btn);
      }
    });
  }

  container.querySelectorAll('a').forEach(a => {
    a.setAttribute('target', '_blank');
    a.setAttribute('rel', 'noopener noreferrer');
  });
}

export function scrollToBottom() {
  elements.messages.scrollTo({
    top: elements.messages.scrollHeight,
    behavior: 'smooth'
  });
}

export function toggleScrollBottomBtn(show) {
  elements.scrollBottomBtn.classList.toggle('visible', show);
}

export function openSidebar() {
  elements.sidebar.classList.add('open');
  elements.sidebarOverlay.classList.add('active');
}

export function closeSidebar() {
  elements.sidebar.classList.remove('open');
  elements.sidebarOverlay.classList.remove('active');
}
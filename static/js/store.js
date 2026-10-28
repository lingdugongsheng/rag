// ==================== 文件说明 ====================
// 前端状态管理模块，数据持久化到 localStorage
//
// 本版关键变化：
// 1. _load 对 localStorage 读/解析全程 try/catch：
//    数据损坏时重置为空对象，避免模块顶层抛异常导致整个前端白屏。
// 2. _save 的 alert 换成 showToast（alert 会阻塞渲染，流式期间弹很丑）。
// 3. 兼容性：仍保留 conversationId 定向更新、citations 字段。

import { showToast } from './utils.js';

class ConversationStore {
  constructor() {
    this.STORAGE_KEY = 'rag_conversations_v2';
    this.CURRENT_KEY = 'rag_current_id';
    this.conversations = {};
    this.currentId = null;
    this._load();
  }

  _load() {
    // ---------- 1. 读 conversations，任何异常都重置，绝不抛 ----------
    let raw = null;
    try {
      raw = localStorage.getItem(this.STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('conversations 不是对象');
      }
      this.conversations = parsed;
    } catch (e) {
      console.warn('[store] conversations 数据损坏，已重置', e);
      this.conversations = {};
      try { localStorage.removeItem(this.STORAGE_KEY); } catch (_) {}
    }

    // ---------- 2. 读 currentId，同样兜底 ----------
    try {
      this.currentId = localStorage.getItem(this.CURRENT_KEY) || null;
    } catch (_) {
      this.currentId = null;
    }

    // ---------- 3. 校正 currentId ----------
    if (Object.keys(this.conversations).length === 0) {
      this.currentId = this.createConversation();
    } else if (!this.currentId || !this.conversations[this.currentId]) {
      this.currentId = Object.keys(this.conversations)[0];
      try { localStorage.setItem(this.CURRENT_KEY, this.currentId); } catch (_) {}
    }
  }

  _save() {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.conversations));
    } catch (e) {
      if (e.name === 'QuotaExceededError') {
        showToast('存储空间不足，请导出并清理旧对话', 'error');
      } else {
        console.error('[store] 保存失败', e);
        showToast('保存对话失败', 'error');
      }
    }
  }

  save() {
    this._save();
  }

  createConversation() {
    const id = 'conv_' + Date.now() + Math.random().toString(36).slice(2, 6);
    this.conversations[id] = {
      id,
      title: '新对话',
      messages: [],
      createdAt: Date.now()
    };
    this.currentId = id;
    try { localStorage.setItem(this.CURRENT_KEY, id); } catch (_) {}
    this._save();
    return id;
  }

  isCurrentConversationEmpty() {
    const conv = this.getCurrent();
    return conv && conv.messages.length === 0 && conv.title === '新对话';
  }

  getCurrent() {
    if (!this.currentId || !this.conversations[this.currentId]) {
      this.currentId = Object.keys(this.conversations)[0] || this.createConversation();
    }
    return this.conversations[this.currentId];
  }

  switchTo(id) {
    if (this.conversations[id]) {
      this.currentId = id;
      try { localStorage.setItem(this.CURRENT_KEY, id); } catch (_) {}
    }
  }

  deleteConversation(id) {
    if (!confirm('确定删除这个对话吗？')) return;

    delete this.conversations[id];

    if (this.currentId === id) {
      const ids = Object.keys(this.conversations);
      this.currentId = ids.length > 0 ? ids[0] : this.createConversation();
      try { localStorage.setItem(this.CURRENT_KEY, this.currentId); } catch (_) {}
    }

    this._save();
  }

  addMessage(role, content) {
    const conv = this.getCurrent();
    const msg = { role, content, timestamp: Date.now() };
    conv.messages.push(msg);

    if (role === 'user' && conv.title === '新对话') {
      conv.title = content.substring(0, 30) + (content.length > 30 ? '...' : '');
    }

    this._save();
    return msg;
  }

  updateLastAssistant(content, persist = true, conversationId = null) {
    const id = conversationId || this.currentId;
    const conv = this.conversations[id];
    if (!conv || conv.messages.length === 0) return;

    const lastMsg = conv.messages[conv.messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.content = content;
      if (persist) this._save();
    }
  }

  setLastAssistantCitations(citations, conversationId = null) {
    const id = conversationId || this.currentId;
    const conv = this.conversations[id];
    if (!conv || conv.messages.length === 0) return;

    const lastMsg = conv.messages[conv.messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.citations = citations;
      this._save();
    }
  }

  removeLastEmptyAssistant(conversationId = null) {
    const id = conversationId || this.currentId;
    const conv = this.conversations[id];
    if (!conv || conv.messages.length === 0) return;

    const last = conv.messages[conv.messages.length - 1];
    if (last.role === 'assistant' && !last.content) {
      conv.messages.pop();
      this._save();
    }
  }

  removeLastMessage() {
    const conv = this.getCurrent();
    conv.messages.pop();
    this._save();
  }

  renameConversation(id, newTitle) {
    if (this.conversations[id]) {
      this.conversations[id].title = newTitle.substring(0, 40) || '未命名对话';
      this._save();
    }
  }

  exportAll() {
    return JSON.stringify(this.conversations, null, 2);
  }

  importConversations(jsonStr) {
    try {
      const data = JSON.parse(jsonStr);
      if (typeof data !== 'object' || data === null || Array.isArray(data)) {
        throw new Error('无效格式');
      }

      let added = 0;
      for (const [id, conv] of Object.entries(data)) {
        if (!this.conversations[id]) {
          this.conversations[id] = conv;
          added++;
        }
      }

      if (added === 0) {
        return { success: false, message: '没有新对话被导入（可能已存在）' };
      }

      if (!this.currentId || !this.conversations[this.currentId]) {
        this.currentId = Object.keys(this.conversations)[0];
      }

      this._save();
      return { success: true, count: added };

    } catch (e) {
      return { success: false, message: '文件格式错误' };
    }
  }
}

export const store = new ConversationStore();
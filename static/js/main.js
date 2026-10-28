// ==================== 文件说明 ====================
// 这是前端应用主入口文件
//
// 本版关键变化：
// 1. handleSend 记录 conversationId，
//    流式回调按 id 定向更新 store，用户切走也不会串流到别的会话
// 2. onCitations 同时写入 store（setLastAssistantCitations），
//    切回原会话后能恢复引用
// 3. cleanupGeneration 只负责全局 UI 状态恢复，
//    会话内清理（空消息）由 onDone / onError 处理

import { $, showToast, downloadFile, initTheme, setTheme, getTheme, isNearBottom } from './utils.js';
import { API } from './api.js';
import { store } from './store.js';
import {
  elements,
  renderAll,
  appendMessage,
  updateMessageContent,
  updateMessageText,
  finalizeMessageContent,
  appendCitations,
  scrollToBottom,
  toggleScrollBottomBtn,
  openSidebar,
  closeSidebar,
} from './renderer.js';

// ==================== 应用状态 ====================
let isGenerating = false;
let cancelStream = null;
let scrollTicking = false;
let uploadedFileCount = 0;

function smartScrollToBottom() {
  if (!scrollTicking) {
    scrollTicking = true;
    requestAnimationFrame(() => {
      if (isNearBottom()) scrollToBottom();
      scrollTicking = false;
    });
  }
}

function init() {
  initTheme();
  renderAll();
  bindEvents();
  autoResizeTextarea();
  initSidebarToggle();
  window.addEventListener('error', () => showToast('应用出现异常，请刷新页面', 'error'));
  window.addEventListener('unhandledrejection', () => showToast('请求失败，请检查网络', 'error'));
}

function bindEvents() {
  $('#send-btn').addEventListener('click', () => {
    if (isGenerating && cancelStream) {
      cancelStream();
      cleanupGeneration();
      showToast('已停止生成', 'info');
      return;
    }
    handleSend();
  });

  $('#user-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  $('#new-chat-btn').addEventListener('click', () => {
    const conv = store.getCurrent();
    if (conv && conv.messages.length === 0 && conv.title === '新对话') {
      showToast('当前已是新对话', 'info');
      return;
    }
    store.createConversation();
    renderAll();
    $('#user-input').focus();
  });

  $('#file-input').addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
    e.target.value = '';
  });

  $('#import-btn').addEventListener('click', () => $('#import-file-input').click());

  $('#import-file-input').addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const result = store.importConversations(ev.target?.result || '');
        if (result.success) {
          showToast(`成功导入 ${result.count} 个对话`, 'success');
          renderAll();
        } else showToast(result.message, 'error');
      };
      reader.readAsText(file);
    }
    e.target.value = '';
  });

  $('#export-btn').addEventListener('click', () => {
    const data = store.exportAll();
    downloadFile(data, `rag-conversations-${Date.now()}.json`, 'application/json');
  });

  $('#theme-toggle-btn').addEventListener('click', () => {
    const themes = ['light', 'dark', 'auto'];
    const current = getTheme();
    const next = themes[(themes.indexOf(current) + 1) % themes.length];
    setTheme(next);
    const labels = { light: '浅色', dark: '深色', auto: '自动' };
    showToast(`主题已切换为 ${labels[next]}`, 'info');
  });

  $('#messages').addEventListener('scroll', () => toggleScrollBottomBtn(!isNearBottom()));

  $('#scroll-bottom-btn').addEventListener('click', () => {
    scrollToBottom();
    toggleScrollBottomBtn(false);
  });

  $('#menu-toggle').addEventListener('click', openSidebar);
  $('#sidebar-overlay').addEventListener('click', closeSidebar);

  document.addEventListener('dragover', (e) => { e.preventDefault(); $('#drop-overlay').classList.add('active'); });
  document.addEventListener('dragleave', (e) => { e.preventDefault(); $('#drop-overlay').classList.remove('active'); });
  document.addEventListener('drop', (e) => {
    e.preventDefault();
    $('#drop-overlay').classList.remove('active');
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      const allowedTypes = ['application/pdf', 'text/plain', 'text/markdown',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      const allowedExts = ['.pdf', '.txt', '.md', '.docx'];
      if (allowedTypes.includes(file.type) || allowedExts.some(ext => file.name.endsWith(ext))) {
        handleFileUpload(file);
      }
    }
  });
}

function autoResizeTextarea() {
  const input = $('#user-input');
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 150) + 'px';
  });
}

function initSidebarToggle() {
  const btn = $('#sidebar-toggle-btn');
  if (btn) {
    const sidebar = $('#sidebar');

    const updateBtnLabel = () => {
      const collapsed = sidebar.classList.contains('collapsed');
      btn.textContent = collapsed ? '▶' : '◀';
      const label = collapsed ? '展开侧边栏' : '折叠侧边栏';
      btn.setAttribute('aria-label', label);
      btn.title = label;
    };

    btn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      updateBtnLabel();
      localStorage.setItem('sidebar_collapsed', sidebar.classList.contains('collapsed'));
    });

    const collapsed = localStorage.getItem('sidebar_collapsed') === 'true';
    if (collapsed) sidebar.classList.add('collapsed');
    updateBtnLabel();
  }
}

async function handleSend() {
  const input = $('#user-input');
  const query = input.value.trim();

  if (!query || isGenerating) return;

  if (query.length > 10000) {
    showToast('消息过长，请限制在10000字符以内', 'error');
    return;
  }

  input.value = '';
  input.style.height = 'auto';

  store.addMessage('user', query);
  if (store.isCurrentConversationEmpty()) renderAll();

  appendMessage('user', query);

  // 记录本次生成的会话 ID
  const conversationId = store.currentId;

  store.addMessage('assistant', '思考中...');
  const aiMessage = appendMessage('assistant', '思考中...');
  aiMessage.classList.add('thinking');

  elements.sendBtn.classList.add('loading');
  elements.sendBtn.setAttribute('aria-label', '停止生成');
  isGenerating = true;

  let firstToken = true;
  let receivedAny = false;
  let accumulated = '';
  let rafScheduled = false;

  // 判断用户当前是否仍停留在原会话
  const onOriginalConversation = () => store.currentId === conversationId;

  cancelStream = API.chatStream(query, {
    onToken: (token) => {
      receivedAny = true;
      if (firstToken) {
        // 只在本会话可见时才动 DOM
        if (onOriginalConversation()) {
          updateMessageContent(aiMessage, '');
          aiMessage.classList.remove('thinking');
        }
        firstToken = false;
      }
      accumulated += token;
      // 定向更新原会话的 store（即使已切走）
      store.updateLastAssistant(accumulated, false, conversationId);

      // 只在本会话可见时才更新 DOM
      if (onOriginalConversation() && !rafScheduled) {
        rafScheduled = true;
        requestAnimationFrame(() => {
          updateMessageText(aiMessage, accumulated);
          rafScheduled = false;
          smartScrollToBottom();
        });
      }
    },

    onCachedAnswer: (answer) => {
      receivedAny = true;
      firstToken = false;
      accumulated = answer;
      store.updateLastAssistant(answer, true, conversationId);
      if (onOriginalConversation()) {
        finalizeMessageContent(aiMessage, answer);
        aiMessage.classList.remove('thinking');
        smartScrollToBottom();
      }
    },

    onCitations: (citations) => {
      // 无论用户是否切走，都写进 store，切回后能恢复
      store.setLastAssistantCitations(citations, conversationId);
      if (onOriginalConversation()) {
        appendCitations(aiMessage, citations);
        smartScrollToBottom();
      }
    },

    onDone: () => {
      if (accumulated) {
        if (onOriginalConversation()) {
          finalizeMessageContent(aiMessage, accumulated);
        }
        store.save();
      } else if (receivedAny) {
        // 有事件但没内容，保留现状
      } else {
        // 什么都没收到：删掉空的思考中消息
        store.removeLastEmptyAssistant(conversationId);
      }
      cleanupGeneration();
    },

    onError: (err) => {
      store.updateLastAssistant(`错误: ${err.message}`, true, conversationId);
      if (onOriginalConversation()) {
        updateMessageContent(aiMessage, `错误: ${err.message}`);
        aiMessage.classList.remove('thinking');
      }
      cleanupGeneration();
      showToast('发送失败，请重试', 'error');
    }
  });
}

function cleanupGeneration() {
  // 只负责全局 UI 状态，不操作会话数据
  isGenerating = false;
  elements.sendBtn.classList.remove('loading', 'processing');
  elements.sendBtn.setAttribute('aria-label', '发送消息');
  cancelStream = null;
  renderAll();
}

function handleFileUpload(file) {
  if (file.size > 50 * 1024 * 1024) {
    showToast('文件大小不能超过50MB', 'error');
    return;
  }

  elements.uploadStatus.textContent = '上传中...';
  elements.uploadProgress.style.display = 'block';
  elements.uploadProgress.style.width = '0%';

  elements.sendBtn.classList.add('processing');
  elements.sendBtn.disabled = true;

  API.uploadFile(file, {
    onStatus: (status) => {
      if (status.status === 'done') {
        uploadedFileCount++;
        showToast(`文件 "${status.fileName}" 处理完成，共 ${status.chunks} 个片段`, 'success');
        elements.uploadStatus.textContent = `✅ 已上传 ${uploadedFileCount} 个文件`;
        elements.uploadProgress.style.width = '100%';
        elements.uploadProgress.style.background = 'var(--accent)';
        elements.uploadProgress.style.animation = '';
        elements.sendBtn.classList.remove('processing');
        elements.sendBtn.disabled = false;
      } else if (status.status === 'error') {
        showToast(status.message, 'error');
        elements.sendBtn.classList.remove('processing');
        elements.sendBtn.disabled = false;
        if (uploadedFileCount > 0) {
          elements.uploadProgress.style.display = 'none';
        } else {
          elements.uploadStatus.textContent = status.message;
          setTimeout(() => {
            elements.uploadStatus.textContent = '';
            elements.uploadProgress.style.display = 'none';
          }, 3000);
        }
      }
    },
    onProgress: (percent) => {
      if (percent === -1) {
        elements.uploadProgress.style.width = '100%';
        elements.uploadProgress.style.background = 'repeating-linear-gradient(90deg, var(--accent) 0px, var(--accent) 10px, transparent 10px, transparent 20px)';
        elements.uploadProgress.style.animation = 'progressStripe 1s linear infinite';
        elements.uploadStatus.textContent = '正在解析文档...';
      } else {
        elements.uploadProgress.style.background = 'var(--accent)';
        elements.uploadProgress.style.animation = '';
        elements.uploadProgress.style.width = `${percent}%`;
        elements.uploadStatus.textContent = `${percent}%`;
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', init);
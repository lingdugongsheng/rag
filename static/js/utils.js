// ==================== 文件说明 ====================
// 这是前端工具模块，提供通用的辅助函数
// 包含：
// 1. DOM 查询
// 2. Markdown 渲染
// 3. Toast 消息
// 4. 文件下载
// 5. 主题管理

/**
 * 获取 DOM 元素（简化版 querySelector）
 * @param {string} selector - CSS 选择器
 * @returns {HTMLElement|null} - 匹配的元素或 null
 */
export function $(selector) {
  return document.querySelector(selector);
}

/**
 * 渲染 Markdown 文本为 HTML
 * @param {string} text - Markdown 文本
 * @returns {string} - 渲染后的 HTML
 */
export function renderMarkdown(text) {
  // 如果没有文本，返回空字符串
  if (!text) return '';
  
  // 初始化 HTML 为原始文本
  let html = text;
  
  // 如果有 marked 库（Markdown 解析器）
  if (window.marked) {
    // 解析 Markdown 为 HTML
    html = window.marked.parse(text) || '';
  }
  
  // 如果有 DOMPurify 库（HTML 净化，防止 XSS）
  if (window.DOMPurify) {
    // 净化 HTML（移除恶意脚本）
    html = window.DOMPurify.sanitize(html);
  }
  
  // 返回处理后的 HTML
  return html;
}

/**
 * 显示 Toast 消息
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型（'info'、'success'、'error'）
 */
export function showToast(message, type = 'info') {
  // 创建 Toast 元素
  const toast = document.createElement('div');
  // 设置类名（包含类型）
  toast.className = `toast toast-${type}`;
  // 设置文本内容
  toast.textContent = message;
  
  // 获取 Toast 容器
  const container = $('#toast-container');
  // 如果容器存在，添加 Toast
  if (container) container.appendChild(toast);
  
  // 3秒后开始淡出
  setTimeout(() => {
    toast.classList.add('fade-out');
    // 淡出动画结束后（300ms）移除元素
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/**
 * 判断是否接近底部
 * @param {HTMLElement} element - 滚动元素（默认消息容器）
 * @param {number} threshold - 距离底部的阈值（默认100像素）
 * @returns {boolean} - 是否接近底部
 */
export function isNearBottom(element = $('#messages'), threshold = 100) {
  // 如果元素不存在，返回 false
  if (!element) return false;
  
  // 计算滚动位置：总高度 - 滚动位置 - 视口高度
  // 如果小于阈值，说明接近底部
  return element.scrollHeight - element.scrollTop - element.clientHeight < threshold;
}

/**
 * 下载文件
 * @param {string} content - 文件内容
 * @param {string} filename - 文件名
 * @param {string} mimeType - MIME 类型（默认纯文本）
 */
export function downloadFile(content, filename, mimeType = 'text/plain') {
  // 创建 Blob 对象（二进制大对象）
  const blob = new Blob([content], { type: mimeType });
  // 创建临时 URL
  const url = URL.createObjectURL(blob);
  
  // 创建 <a> 标签
  const a = document.createElement('a');
  // 设置下载链接
  a.href = url;
  // 设置文件名
  a.download = filename;
  
  // 添加到页面（必须添加到 DOM 才能触发下载）
  document.body.appendChild(a);
  // 触发点击事件
  a.click();
  // 移除元素
  document.body.removeChild(a);
  // 释放 URL（避免内存泄漏）
  URL.revokeObjectURL(url);
}

/**
 * 获取当前主题
 * @returns {string} - 主题名称（'light'、'dark'、'auto'）
 */
export function getTheme() {
  // 从 localStorage 读取，默认为 'light'
  return localStorage.getItem('rag_theme') || 'light';
}

/**
 * 设置主题
 * @param {string} theme - 主题名称（'light'、'dark'、'auto'）
 */
export function setTheme(theme) {
  // 保存到 localStorage
  localStorage.setItem('rag_theme', theme);
  
  // 获取 HTML 根元素
  const html = document.documentElement;
  // 先移除深色主题类
  html.classList.remove('theme-dark');
  
  // 根据主题设置
  if (theme === 'dark') {
    // 添加深色主题类
    html.classList.add('theme-dark');
  } else if (theme === 'auto') {
    // 自动模式：根据系统设置判断
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      html.classList.add('theme-dark');
    }
  }
  
  // 动态切换代码高亮主题
  const hljsLink = document.getElementById('hljs-theme');
  if (hljsLink) {
    // 判断是否为深色模式
    const isDark = html.classList.contains('theme-dark');
    // 设置对应的高亮主题
    hljsLink.href = isDark
      ? 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css'
      : 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-light.min.css';
  }
}

/**
 * 初始化主题
 */
export function initTheme() {
  // 应用保存的主题
  setTheme(getTheme());
  
  // 监听系统主题变化（仅在自动模式下生效）
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (getTheme() === 'auto') setTheme('auto');
  });
}
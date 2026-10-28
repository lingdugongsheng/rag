# 前端代码汇总

## 目录结构
```
static/
├── index.html      # 页面结构
├── styles.css      # 样式文件
└── js/
    ├── main.js     # 应用主入口
    ├── api.js      # API 客户端
    ├── store.js    # 状态管理
    ├── renderer.js # DOM 渲染
    └── utils.js    # 工具函数
```

---

## 1. index.html - 页面结构

```html
<!-- ==================== 文件说明 ==================== -->
<!-- 这是前端页面的 HTML 结构 -->
<!-- 页面布局：左侧侧边栏（对话历史）+ 右侧主面板（聊天区域） -->
<!-- 技术栈：原生 HTML + CSS + JavaScript（无框架） -->

<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <!-- 设置字符编码为 UTF-8，支持中文 -->
  <meta charset="UTF-8">
  <!-- 响应式视图设置：宽度自适应设备，初始缩放为1.0，支持刘海屏 -->
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <!-- 页面描述，用于 SEO -->
  <meta name="description" content="基于RAG的智能知识库问答系统">
  <!-- 页面标题 -->
  <title>RAG 智能问答</title>
  <!-- 网页图标（使用 emoji 🧠） -->
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>🧠</text></svg>">
  <!-- 引入自定义样式文件 -->
  <link rel="stylesheet" href="/static/styles.css">
  <!-- 引入代码高亮主题（默认为深色主题） -->
  <link rel="stylesheet" id="hljs-theme" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
  <!-- 引入代码高亮库（defer 表示页面加载完成后再执行） -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js" defer></script>
  <!-- 引入 Markdown 解析库 -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js" defer></script>
  <!-- 引入 HTML 净化库（防止 XSS 攻击） -->
  <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.8/dist/purify.min.js" defer></script>
  <!-- 引入主 JavaScript 文件（module 模式） -->
  <script type="module" src="/static/js/main.js" defer></script>
</head>
<body>
  <!-- 侧边栏遮罩层（移动端使用，点击关闭侧边栏） -->
  <div class="sidebar-overlay" id="sidebar-overlay"></div>

  <!-- 侧边栏：包含对话历史和操作按钮 -->
  <aside class="sidebar" id="sidebar" role="navigation" aria-label="对话历史">
    <!-- 侧边栏头部：标题和折叠按钮 -->
    <div class="sidebar-header">
      <span>🧠 RAG System</span>  <!-- 系统标题 -->
      <!-- 折叠/展开侧边栏按钮 -->
      <button class="sidebar-toggle-btn" id="sidebar-toggle-btn" aria-label="折叠侧边栏" title="折叠侧边栏">◀</button>
    </div>
    
    <!-- 新对话按钮 -->
    <button class="new-chat-btn" id="new-chat-btn" aria-label="开启新对话">
      <span aria-hidden="true">＋</span> <span class="btn-text">新对话</span>
    </button>
    
    <!-- 对话历史列表 -->
    <div class="history-list" id="history-list" role="list" aria-label="历史对话列表"></div>
    
    <!-- 侧边栏底部：导出、导入、主题切换按钮 -->
    <div class="sidebar-footer">
      <div class="footer-actions">
        <button class="footer-btn" id="export-btn" aria-label="导出对话" title="导出全部对话">📤</button>
        <button class="footer-btn" id="import-btn" aria-label="导入对话" title="导入对话备份">📥</button>
        <button class="footer-btn" id="theme-toggle-btn" aria-label="切换主题" title="切换浅色/深色/自动">🌓</button>
      </div>
      <!-- 隐藏的文件导入输入框 -->
      <input type="file" id="import-file-input" accept=".json" hidden>
    </div>
  </aside>

  <!-- 主面板：聊天区域 -->
  <main class="main-panel" id="main-panel">
    <!-- 聊天头部：菜单按钮和对话标题 -->
    <header class="chat-header">
      <button class="menu-toggle" id="menu-toggle" aria-label="切换侧边栏" aria-expanded="false">☰</button>
      <span id="chat-header-title">新对话</span>
    </header>
    
    <!-- 消息容器：显示所有消息 -->
    <div class="messages-container" id="messages" role="log" aria-live="polite" aria-label="对话内容">
      <!-- 空状态：没有消息时显示 -->
      <div class="empty-state" id="empty-state">
        <div class="empty-icon">📚</div>
        <h3>欢迎使用 RAG 智能问答</h3>
        <p>上传文档后即可开始提问</p>
      </div>
    </div>
    
    <!-- 回到底部按钮 -->
    <button class="scroll-bottom-btn" id="scroll-bottom-btn" aria-label="回到底部" title="回到底部">↓</button>
    
    <!-- 输入区域：上传文件 + 输入框 + 发送按钮 -->
    <footer class="input-area">
      <!-- 上传区域 -->
      <div class="upload-area" id="upload-area">
        <label class="file-label" for="file-input" title="上传文档" aria-label="上传文档">
          <span class="file-label-icon">📎</span>
          <span class="file-label-text">上传文档</span>
        </label>
        <!-- 上传进度条 -->
        <div class="upload-progress" id="upload-progress-bar" style="display:none;"></div>
        <!-- 上传状态文本 -->
        <span class="upload-status-text" id="upload-status-text" aria-live="polite"></span>
      </div>
      <!-- 隐藏的文件选择输入框 -->
      <input type="file" id="file-input" accept=".pdf,.txt,.md,.docx" hidden>
      
      <!-- 输入框包装器 -->
      <div class="input-wrapper">
        <textarea id="user-input" rows="1" placeholder="输入您的问题... (Enter 发送，Shift+Enter 换行)"
                  aria-label="输入问题"></textarea>
      </div>
      
      <!-- 发送按钮 -->
      <button class="send-btn" id="send-btn" aria-label="发送消息">
        <!-- 发送图标 -->
        <svg class="send-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>
        <!-- 加载动画 -->
        <span class="spinner" aria-hidden="true"></span>
        <!-- 停止图标 -->
        <svg class="stop-icon" viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
      </button>
    </footer>
  </main>

  <!-- 拖拽上传覆盖层（用户拖拽文件时显示） -->
  <div id="drop-overlay" class="drop-overlay" aria-hidden="true">
    <div class="drop-message">📂 释放文件以上传</div>
  </div>

  <!-- Toast 消息容器（用于显示提示信息） -->
  <div id="toast-container" aria-live="polite" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:9999;pointer-events:none;"></div>
</body>
</html>
```

---

## 2. styles.css - 样式文件

```css
/* ==================== 文件说明 ==================== */
/* 这是前端页面的 CSS 样式文件 */
/* 包含主题变量、布局样式、组件样式、响应式设计 */
/* 支持浅色/深色两种主题 */

/* ========== 主题变量定义 ========== */
/* 使用 CSS 变量定义颜色、间距、阴影等，方便切换主题 */
:root {
  /* 主色调 */
  --primary: #00838f;              /* 主色（青蓝色） */
  --primary-light: #006b75;        /* 主色暗一点的版本 */
  --accent: #1e9ed5;               /* 强调色（亮蓝色） */
  --accent-light: #43b5e3;         /* 强调色亮一点的版本 */
  
  /* 侧边栏颜色 */
  --sidebar-bg: #06121e;           /* 侧边栏背景 */
  --sidebar-hover: #0f2033;        /* 悬停时的背景 */
  --sidebar-active: #162a3f;       /* 激活状态的背景 */
  --sidebar-active-border: none;    /* 激活状态的边框（不使用） */
  
  /* 聊天区域颜色 */
  --chat-bg: #eaf3f8;              /* 聊天背景 */
  --user-msg-bg: #c2dcee;          /* 用户消息背景 */
  --ai-msg-bg: #ffffff;            /* AI 消息背景 */
  --border: #9db8c8;               /* 边框颜色 */
  
  /* 文字颜色 */
  --text-primary: #0a1929;         /* 主要文字颜色 */
  --text-secondary: #4a6278;       /* 次要文字颜色 */
  
  /* 阴影 */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);    /* 小阴影 */
  --shadow: 0 4px 12px rgba(0, 80, 100, 0.08);  /* 中等阴影 */
  --shadow-lg: 0 8px 24px rgba(0, 80, 100, 0.12); /* 大阴影 */
  
  /* 圆角 */
  --radius: 20px;                  /* 大圆角 */
  --radius-sm: 12px;               /* 小圆角 */
  
  /* 过渡动画 */
  --transition: 0.2s ease;         /* 过渡时间和缓动函数 */
  
  /* 字体 */
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;  /* 等宽字体（代码用） */
  
  /* 其他 */
  --overlay-bg: rgba(0,0,0,0.4);   /* 遮罩层背景 */
  --code-bg: #0a1a2b;              /* 代码块背景 */
  --code-text: #b0e0ff;            /* 代码文字颜色 */
}

/* ========== 深色主题变量 ========== */
/* 覆盖浅色主题的变量，实现深色模式 */
.theme-dark {
  --primary: #159baa;
  --primary-light: #007983;
  --accent: #34b7d6;
  --accent-light: #5dc7e0;
  --sidebar-bg: #040b15;
  --sidebar-hover: #0b1828;
  --sidebar-active: #102138;
  --sidebar-active-border: none;
  --chat-bg: #020810;
  --user-msg-bg: #091524;
  --ai-msg-bg: #06101e;
  --border: #112535;
  --text-primary: #c5dff5;
  --text-secondary: #6d8fa8;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
  --shadow: 0 4px 12px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.5);
  --overlay-bg: rgba(0,0,0,0.7);
  --code-bg: #040b15;
  --code-text: #bee0f5;
  color-scheme: dark;  /* 告诉浏览器使用深色模式的滚动条等 */
}

/* 深色主题下的额外样式调整 */
.theme-dark body { color-scheme: dark; }
.theme-dark .input-wrapper { background: #091524; }
.theme-dark textarea { color: #c5dff5; }
.theme-dark .chat-header { background: rgba(2,8,16,0.8); backdrop-filter: blur(12px); color: #c5dff5; }
.theme-dark .input-area { background: rgba(2,8,16,0.85); backdrop-filter: blur(12px); }

/* ========== 全局基础样式 ========== */
/* 重置默认样式，统一基础设置 */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;  /* 字体栈 */
  background: var(--chat-bg);        /* 背景色 */
  height: 100vh;                     /* 高度占满屏幕 */
  display: flex;                     /* 弹性布局 */
  overflow: hidden;                  /* 隐藏滚动条 */
  color: var(--text-primary);        /* 文字颜色 */
  transition: background 0.3s, color 0.3s;  /* 主题切换动画 */
  touch-action: manipulation;        /* 优化移动端触摸体验 */
}

/* ========== 侧边栏样式 ========== */
.sidebar {
  width: 280px;                     /* 宽度 */
  background: var(--sidebar-bg);     /* 背景色 */
  color: #fff;                      /* 文字颜色 */
  display: flex; flex-direction: column;  /* 垂直布局 */
  box-shadow: 2px 0 24px rgba(0,0,0,0.25);  /* 右侧阴影 */
  z-index: 20;                      /* 层级 */
  transition: width var(--transition), transform var(--transition);  /* 过渡动画 */
  pointer-events: auto;              /* 响应鼠标事件 */
  flex-shrink: 0;                   /* 不缩小 */
}

/* 折叠状态的侧边栏 */
.sidebar.collapsed {
  width: 60px;                      /* 折叠后宽度 */
}

/* 折叠时隐藏文字 */
.sidebar.collapsed .sidebar-header span,
.sidebar.collapsed .btn-text,
.sidebar.collapsed .history-item span:first-child,
.sidebar.collapsed .footer-btn span {
  display: none;
}

/* 侧边栏头部 */
.sidebar-header {
  padding: 20px 16px;               /* 内边距 */
  display: flex;                    /* 水平布局 */
  justify-content: space-between;    /* 两端对齐 */
  align-items: center;              /* 垂直居中 */
  font-weight: 700;                 /* 粗体 */
  font-size: 1.1rem;                /* 字体大小 */
  border-bottom: 1px solid rgba(255,255,255,0.08);  /* 底部边框 */
  letter-spacing: 0.5px;            /* 字间距 */
  /* 渐变色文字效果 */
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 折叠/展开按钮 */
.sidebar-toggle-btn {
  background: rgba(255,255,255,0.1);  /* 半透明背景 */
  border: none;                      /* 无边框 */
  color: #cbd5e1;                   /* 图标颜色 */
  font-size: 1rem;                  /* 字体大小 */
  cursor: pointer;                  /* 鼠标指针 */
  padding: 4px 8px;                 /* 内边距 */
  border-radius: 6px;               /* 圆角 */
  display: flex; align-items: center;  /* 居中 */
  transition: background 0.2s, color 0.2s;  /* 过渡动画 */
  -webkit-text-fill-color: #cbd5e1; /* 覆盖渐变色 */
}

/* 悬停效果 */
.sidebar-toggle-btn:hover { background: rgba(255,255,255,0.2); color: white; }

/* 新对话按钮 */
.new-chat-btn {
  margin: 16px 16px 8px;            /* 外边距 */
  padding: 10px 16px;               /* 内边距 */
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 50%);  /* 渐变背景 */
  border: none;                      /* 无边框 */
  border-radius: var(--radius-sm);   /* 圆角 */
  color: white;                      /* 文字颜色 */
  font-weight: 600;                 /* 粗体 */
  cursor: pointer;                  /* 鼠标指针 */
  display: flex; align-items: center; gap: 8px;  /* 水平布局，有间距 */
  transition: transform 0.15s, box-shadow 0.15s;  /* 过渡动画 */
  box-shadow: 0 4px 12px rgba(0, 130, 150, 0.3);  /* 阴影 */
}

/* 悬停效果：上浮 + 阴影变大 */
.new-chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 130, 150, 0.45);
}

/* 历史列表 */
.history-list {
  flex: 1;                          /* 占据剩余空间 */
  overflow-y: auto;                 /* 垂直滚动 */
  padding: 8px 12px;                /* 内边距 */
  display: flex; flex-direction: column; gap: 2px;  /* 垂直布局，有间距 */
}

/* 历史项 */
.history-item {
  padding: 10px 14px;               /* 内边距 */
  margin: 2px 0;                    /* 外边距 */
  border-radius: var(--radius-sm);   /* 圆角 */
  cursor: pointer;                  /* 鼠标指针 */
  display: flex; justify-content: space-between; align-items: center;  /* 水平布局，两端对齐 */
  color: #cbd5e1;                   /* 文字颜色 */
  transition: background var(--transition), color var(--transition);  /* 过渡动画 */
  word-break: break-word;           /* 自动换行 */
  position: relative;               /* 相对定位（用于弹出菜单） */
}

/* 悬停效果 */
.history-item:hover { background: var(--sidebar-hover); color: #fff; }

/* 激活状态 */
.history-item.active {
  background: var(--sidebar-active);
  color: #fff;
  font-weight: 500;
}

/* 对话标题文本 */
.history-item .item-title {
  flex: 1;                          /* 占据剩余空间 */
  overflow: hidden;                 /* 隐藏溢出 */
  text-overflow: ellipsis;          /* 省略号 */
  white-space: nowrap;              /* 不换行 */
}

/* 三点菜单按钮 */
.item-menu-btn {
  background: none;                 /* 无背景 */
  border: none;                      /* 无边框 */
  color: #64748b;                   /* 颜色 */
  cursor: pointer;                  /* 鼠标指针 */
  padding: 2px 6px;                 /* 内边距 */
  border-radius: 6px;               /* 圆角 */
  font-size: 1.2rem;                /* 字体大小 */
  line-height: 1;                   /* 行高 */
  transition: color var(--transition), background var(--transition);  /* 过渡动画 */
  margin-left: 4px;                 /* 左边距 */
  flex-shrink: 0;                   /* 不缩小 */
  display: none;                    /* 默认隐藏 */
}

/* 悬停时显示菜单按钮 */
.history-item:hover .item-menu-btn {
  display: block;
}

/* 菜单按钮悬停效果 */
.item-menu-btn:hover {
  color: white;
  background: rgba(255,255,255,0.1);
}

/* 弹出菜单 */
.popup-menu {
  position: absolute;               /* 绝对定位 */
  right: 10px;                      /* 右边距 */
  top: 100%;                        /* 顶部在父元素下方 */
  background: #1e2a3a;             /* 背景色 */
  border: 1px solid rgba(255,255,255,0.15);  /* 边框 */
  border-radius: 8px;               /* 圆角 */
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);  /* 阴影 */
  z-index: 50;                      /* 层级 */
  min-width: 100px;                 /* 最小宽度 */
  padding: 4px 0;                   /* 内边距 */
  display: none;                    /* 默认隐藏 */
}

/* 显示弹出菜单 */
.popup-menu.show {
  display: block;
}

/* 弹出菜单项 */
.popup-menu-item {
  padding: 8px 16px;                /* 内边距 */
  color: #cbd5e1;                   /* 颜色 */
  cursor: pointer;                  /* 鼠标指针 */
  font-size: 0.9rem;                /* 字体大小 */
  transition: background 0.15s;     /* 过渡动画 */
  white-space: nowrap;              /* 不换行 */
}

/* 悬停效果 */
.popup-menu-item:hover {
  background: rgba(255,255,255,0.1);
  color: white;
}

/* 危险操作（删除） */
.popup-menu-item.danger {
  color: #fca5a5;                   /* 红色 */
}

/* 危险操作悬停效果 */
.popup-menu-item.danger:hover {
  background: rgba(252, 165, 165, 0.15);
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: 12px 16px;               /* 内边距 */
  border-top: 1px solid rgba(255,255,255,0.08);  /* 顶部边框 */
  display: flex; justify-content: center;  /* 居中 */
}

/* 底部按钮组 */
.footer-actions { display: flex; gap: 8px; }

/* 底部按钮 */
.footer-btn {
  background: rgba(255,255,255,0.1);  /* 半透明背景 */
  border: none;                      /* 无边框 */
  color: #cbd5e1;                   /* 颜色 */
  font-size: 1.2rem;                /* 字体大小 */
  padding: 8px 12px;                /* 内边距 */
  border-radius: 8px;               /* 圆角 */
  cursor: pointer;                  /* 鼠标指针 */
  transition: background var(--transition), color var(--transition), transform 0.1s;  /* 过渡动画 */
}

/* 悬停效果 */
.footer-btn:hover { background: rgba(255,255,255,0.2); color: white; transform: scale(1.05); }

/* ========== 主面板样式 ========== */
.main-panel {
  flex: 1;                          /* 占据剩余空间 */
  display: flex; flex-direction: column;  /* 垂直布局 */
  background: var(--chat-bg);        /* 背景色 */
  position: relative;               /* 相对定位 */
  transition: background 0.3s;      /* 过渡动画 */
}

/* 聊天头部 */
.chat-header {
  padding: 12px 24px;               /* 内边距 */
  font-weight: 600;                 /* 粗体 */
  color: var(--text-primary);        /* 文字颜色 */
  background: rgba(234, 243, 248, 0.75);  /* 半透明背景 */
  backdrop-filter: blur(12px);      /* 模糊效果 */
  border-bottom: 1px solid var(--border);  /* 底部边框 */
  display: flex; align-items: center; gap: 12px;  /* 水平布局 */
  transition: background 0.3s;      /* 过渡动画 */
}

/* 菜单按钮（移动端显示） */
.menu-toggle { display: none; background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-primary); }

/* 消息容器 */
.messages-container {
  flex: 1;                          /* 占据剩余空间 */
  overflow-y: auto;                 /* 垂直滚动 */
  padding: 24px;                    /* 内边距 */
  display: flex; flex-direction: column; gap: 20px;  /* 垂直布局，有间距 */
  scroll-behavior: smooth;          /* 平滑滚动 */
  -webkit-overflow-scrolling: touch; /* 移动端平滑滚动 */
}

/* 空状态 */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;  /* 居中 */
  height: 100%;                     /* 高度 */
  color: var(--text-secondary);     /* 文字颜色 */
}

/* 空状态图标 */
.empty-icon { font-size: 4.5rem; margin-bottom: 20px; animation: float 3s ease-in-out infinite; }

/* 浮动动画 */
@keyframes float { 0%,100% { transform: translateY(0px); } 50% { transform: translateY(-12px); } }

/* 空状态标题 */
.empty-state h3 { margin-bottom: 8px; color: var(--text-primary); font-weight: 600; }

/* ========== 消息样式 ========== */
.message {
  display: flex; gap: 12px;         /* 水平布局，有间距 */
  animation: msgSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);  /* 进入动画 */
}

/* 消息进入动画 */
@keyframes msgSlideIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }

/* 用户消息：右侧对齐 */
.message.user { flex-direction: row-reverse; }

/* 头像 */
.avatar {
  width: 38px; height: 38px;        /* 大小 */
  border-radius: 50%;               /* 圆形 */
  display: flex; align-items: center; justify-content: center;  /* 居中 */
  font-size: 1.3rem;                /* 字体大小 */
  font-weight: 700;                 /* 粗体 */
  flex-shrink: 0;                   /* 不缩小 */
  box-shadow: var(--shadow-sm);     /* 阴影 */
}

/* 用户头像 */
.user .avatar { background: var(--primary); color: white; }

/* AI 头像 */
.assistant .avatar { background: linear-gradient(135deg, var(--accent) 0%, var(--primary) 100%); color: white; }

/* 消息内容 */
.message-content {
  max-width: 75%;                   /* 最大宽度 */
  padding: 14px 18px;               /* 内边距 */
  border-radius: var(--radius-sm);   /* 圆角 */
  background: var(--ai-msg-bg);     /* 背景色 */
  box-shadow: var(--shadow), var(--shadow-sm);  /* 阴影 */
  line-height: 1.65;                /* 行高 */
  word-wrap: break-word;            /* 自动换行 */
  color: var(--text-primary);        /* 文字颜色 */
  position: relative;               /* 相对定位 */
  transition: box-shadow 0.2s;      /* 过渡动画 */
}

/* 悬停效果 */
.message-content:hover { box-shadow: var(--shadow-lg); }

/* 用户消息背景 */
.user .message-content { background: var(--user-msg-bg); }

/* 思考中样式 */
.message.thinking .message-content {
  font-style: italic;               /* 斜体 */
  color: var(--text-secondary);     /* 次要颜色 */
  background: rgba(0,0,0,0.02);    /* 淡色背景 */
  box-shadow: var(--shadow-sm);     /* 小阴影 */
}

/* 深色主题下的思考中样式 */
.theme-dark .message.thinking .message-content {
  background: rgba(255,255,255,0.02);
}

/* 代码块样式 */
.message-content pre {
  background: var(--code-bg);       /* 代码背景 */
  color: var(--code-text);          /* 代码文字 */
  padding: 16px;                    /* 内边距 */
  border-radius: 10px;              /* 圆角 */
  overflow-x: auto;                 /* 水平滚动 */
  position: relative;               /* 相对定位（用于复制按钮） */
  margin: 8px 0;                    /* 外边距 */
}

/* 行内代码样式 */
.message-content code {
  background: rgba(0,0,0,0.04);    /* 淡色背景 */
  padding: 2px 6px;                 /* 内边距 */
  border-radius: 4px;               /* 圆角 */
  font-family: var(--font-mono);    /* 等宽字体 */
  font-size: 0.9em;                 /* 字体大小 */
}

/* 代码块内的代码不应用行内样式 */
.message-content pre code { background: none; padding: 0; }

/* 链接样式 */
.message-content a {
  color: var(--primary);            /* 主色调 */
  text-decoration: none;            /* 无下划线 */
  border-bottom: 1px solid rgba(0, 130, 150, 0.3);  /* 底部边框 */
  transition: border-color 0.2s;    /* 过渡动画 */
}

/* 链接悬停效果 */
.message-content a:hover { border-bottom-color: var(--primary); }

/* 图片样式 */
.message-content img { max-width: 100%; border-radius: 8px; }

/* 复制代码按钮 */
.copy-code-btn {
  position: absolute;               /* 绝对定位 */
  top: 8px; right: 8px;             /* 位置 */
  width: 28px; height: 28px;        /* 大小 */
  border-radius: 50%;               /* 圆形 */
  background: rgba(255,255,255,0.15);  /* 半透明背景 */
  border: none;                      /* 无边框 */
  color: white;                      /* 颜色 */
  cursor: pointer;                  /* 鼠标指针 */
  font-size: 0.8rem;                /* 字体大小 */
  display: flex; align-items: center; justify-content: center;  /* 居中 */
  opacity: 0;                       /* 默认透明 */
  transition: opacity 0.2s, background 0.2s;  /* 过渡动画 */
  backdrop-filter: blur(4px);       /* 模糊效果 */
}

/* 悬停时显示复制按钮 */
.message-content pre:hover .copy-code-btn { opacity: 1; }

/* 复制按钮悬停效果 */
.copy-code-btn:hover { background: rgba(255,255,255,0.3); }

/* ========== 输入区域样式 ========== */
.input-area {
  padding: 16px 24px 20px;          /* 内边距 */
  padding-bottom: calc(20px + env(safe-area-inset-bottom));  /* 适配刘海屏 */
  background: rgba(234, 243, 248, 0.75);  /* 半透明背景 */
  backdrop-filter: blur(12px);      /* 模糊效果 */
  border-top: 1px solid var(--border);  /* 顶部边框 */
  display: flex; align-items: flex-end; gap: 8px;  /* 水平布局，底部对齐 */
  transition: background 0.3s;      /* 过渡动画 */
}

/* 上传区域 */
.upload-area { display: flex; align-items: center; gap: 8px; margin-right: 4px; position: relative; }

/* 文件标签 */
.file-label {
  display: flex; align-items: center; gap: 6px;  /* 水平布局 */
  padding: 8px 14px;                /* 内边距 */
  border-radius: 20px;              /* 圆角 */
  background: rgba(0,0,0,0.03);    /* 淡色背景 */
  cursor: pointer;                  /* 鼠标指针 */
  transition: background var(--transition), transform 0.1s;  /* 过渡动画 */
  white-space: nowrap;              /* 不换行 */
  font-size: 0.9rem;                /* 字体大小 */
  color: var(--text-secondary);     /* 次要颜色 */
}

/* 悬停效果 */
.file-label:hover { background: rgba(0,0,0,0.06); transform: translateY(-1px); }

/* 上传状态文本 */
.upload-status-text {
  font-size: 0.8rem;                /* 字体大小 */
  color: var(--primary);            /* 主色调 */
  max-width: 140px;                 /* 最大宽度 */
  overflow: hidden;                 /* 隐藏溢出 */
  text-overflow: ellipsis;          /* 省略号 */
  white-space: nowrap;              /* 不换行 */
}

/* 上传进度条 */
.upload-progress {
  position: absolute;               /* 绝对定位 */
  bottom: -4px; left: 0;            /* 位置 */
  height: 3px;                      /* 高度 */
  background: var(--primary);       /* 颜色 */
  border-radius: 0 3px 3px 0;      /* 圆角 */
  transition: width 0.3s ease;      /* 过渡动画 */
  width: 0%;                        /* 初始宽度 */
}

/* 输入框包装器 */
.input-wrapper {
  flex: 1;                          /* 占据剩余空间 */
  background: white;                /* 背景色 */
  border-radius: 24px;              /* 圆角 */
  border: 1px solid var(--border);  /* 边框 */
  padding: 8px 16px;                /* 内边距 */
  display: flex; align-items: flex-end;  /* 水平布局，底部对齐 */
  box-shadow: var(--shadow-sm);     /* 阴影 */
  transition: border var(--transition), box-shadow 0.2s, background 0.3s;  /* 过渡动画 */
}

/* 聚焦效果 */
.input-wrapper:focus-within { 
  border-color: var(--primary); 
  box-shadow: 0 0 0 3px rgba(0, 130, 150, 0.2);
}

/* 文本框 */
textarea {
  flex: 1;                          /* 占据剩余空间 */
  border: none;                      /* 无边框 */
  outline: none;                    /* 无焦点轮廓 */
  resize: none;                     /* 禁止调整大小 */
  font-size: 0.95rem;               /* 字体大小 */
  line-height: 1.5;                /* 行高 */
  max-height: 150px;                /* 最大高度 */
  overflow-y: auto;                 /* 垂直滚动 */
  font-family: inherit;             /* 继承字体 */
  color: var(--text-primary);        /* 文字颜色 */
  background: transparent;          /* 透明背景 */
  transition: height 0.15s ease;    /* 高度过渡 */
}

/* 占位符样式 */
textarea::placeholder { color: #9ca3af; opacity: 1; }

/* 发送按钮 */
.send-btn {
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);  /* 渐变背景 */
  border: none;                      /* 无边框 */
  border-radius: 50%;               /* 圆形 */
  width: 42px; height: 42px;        /* 大小 */
  display: flex; align-items: center; justify-content: center;  /* 居中 */
  color: white;                      /* 颜色 */
  cursor: pointer;                  /* 鼠标指针 */
  transition: transform 0.15s, box-shadow 0.15s;  /* 过渡动画 */
  box-shadow: 0 4px 12px rgba(0, 130, 150, 0.3);  /* 阴影 */
  margin-left: 8px;                 /* 左边距 */
  flex-shrink: 0;                   /* 不缩小 */
}

/* 按下效果 */
.send-btn:active:not(:disabled) { transform: scale(0.93); }

/* 悬停效果 */
.send-btn:hover:not(:disabled) { transform: scale(1.06); box-shadow: 0 6px 16px rgba(0, 130, 150, 0.4); }

/* 禁用状态 */
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

/* 发送按钮内的图标控制 */
.send-btn .spinner,
.send-btn .stop-icon { display: none; }
.send-btn.loading .send-icon { display: none; }
.send-btn.loading .stop-icon { display: block; }
.send-btn.processing .send-icon { display: none; }
.send-btn.processing .spinner { display: inline-block; }

/* 加载动画 */
.spinner {
  width: 20px; height: 20px;        /* 大小 */
  border: 2px solid white;          /* 白色边框 */
  border-top-color: transparent;    /* 顶部透明 */
  border-radius: 50%;               /* 圆形 */
  animation: spin 0.6s linear infinite;  /* 旋转动画 */
}

/* 旋转动画 */
@keyframes spin { to { transform: rotate(360deg); } }

/* ========== 回到底部按钮 ========== */
.scroll-bottom-btn {
  position: fixed;                  /* 固定定位 */
  bottom: 90px; right: 30px;        /* 位置 */
  width: 44px; height: 44px;        /* 大小 */
  border-radius: 50%;               /* 圆形 */
  background: var(--ai-msg-bg);     /* 背景色 */
  border: 1px solid var(--border);  /* 边框 */
  box-shadow: var(--shadow-lg);     /* 阴影 */
  display: flex; align-items: center; justify-content: center;  /* 居中 */
  cursor: pointer;                  /* 鼠标指针 */
  z-index: 10;                      /* 层级 */
  opacity: 0;                       /* 默认透明 */
  transform: translateY(20px) scale(0.9);  /* 默认向下偏移 */
  transition: opacity 0.25s, transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);  /* 过渡动画 */
  pointer-events: none;             /* 默认不响应事件 */
  color: var(--primary);            /* 颜色 */
  font-size: 1.3rem;                /* 字体大小 */
  font-weight: bold;                /* 粗体 */
}

/* 显示状态 */
.scroll-bottom-btn.visible { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }

/* 悬停效果 */
.scroll-bottom-btn:hover { transform: scale(1.08); }

/* ========== 拖拽上传覆盖层 ========== */
.drop-overlay {
  display: none;                    /* 默认隐藏 */
  position: fixed; inset: 0;        /* 覆盖整个屏幕 */
  background: var(--overlay-bg);    /* 遮罩背景 */
  z-index: 100;                     /* 最高层级 */
  align-items: center; justify-content: center;  /* 居中 */
  pointer-events: none;             /* 默认不响应事件 */
}

/* 激活状态 */
.drop-overlay.active { display: flex; pointer-events: auto; }

/* 拖拽消息 */
.drop-message {
  background: var(--ai-msg-bg);     /* 背景色 */
  padding: 40px 60px;               /* 内边距 */
  border-radius: var(--radius);     /* 圆角 */
  font-size: 1.5rem;                /* 字体大小 */
  color: var(--text-primary);        /* 文字颜色 */
  box-shadow: var(--shadow-lg);     /* 阴影 */
  border: 2px dashed var(--primary);  /* 虚线边框 */
  animation: pulse 1.5s ease-in-out infinite;  /* 脉冲动画 */
}

/* 脉冲动画 */
@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.02); } }

/* ========== 滚动条样式 ========== */
::-webkit-scrollbar { width: 6px; }        /* 宽度 */
::-webkit-scrollbar-track { background: transparent; }  /* 轨道背景 */
::-webkit-scrollbar-thumb { background: #b0c4de; border-radius: 3px; }  /* 滑块 */
::-webkit-scrollbar-thumb:hover { background: #7b9bc0; }  /* 滑块悬停 */

/* 深色主题下的滚动条 */
.theme-dark ::-webkit-scrollbar-thumb { background: #1a3b50; }
.theme-dark ::-webkit-scrollbar-thumb:hover { background: #2a4b60; }

/* ========== 移动端响应式 ========== */
/* 当屏幕宽度小于768px时应用以下样式 */
@media (max-width: 768px) {
  /* 侧边栏改为浮动 */
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0;  /* 覆盖左侧 */
    transform: translateX(-100%);  /* 初始隐藏在左侧 */
    z-index: 30;                     /* 层级 */
    width: 280px;                    /* 宽度 */
    transition: transform var(--transition);  /* 过渡动画 */
  }
  
  /* 打开状态 */
  .sidebar.open { transform: translateX(0); }
  
  /* 移动端不折叠 */
  .sidebar.collapsed { width: 280px; }
  
  /* 遮罩层 */
  .sidebar-overlay {
    display: none;                    /* 默认隐藏 */
    position: fixed; inset: 0;        /* 覆盖整个屏幕 */
    background: var(--overlay-bg);    /* 遮罩背景 */
    z-index: 25;                     /* 层级 */
  }
  
  /* 显示遮罩层 */
  .sidebar-overlay.active { display: block; }
  
  /* 显示菜单按钮 */
  .menu-toggle { display: block; }
  
  /* 消息内容更宽 */
  .message-content { max-width: 92%; }
  
  /* 上传区域调整 */
  .upload-area { margin-right: 0; }
  .file-label-text { display: none; }
  .file-label { padding: 8px 12px; }
  
  /* 回到底部按钮位置调整 */
  .scroll-bottom-btn { right: 16px; bottom: 85px; }
  
  /* 隐藏侧边栏折叠按钮 */
  .sidebar-toggle-btn { display: none; }
}

/* ========== 无障碍访问样式 ========== */
/* 焦点样式（键盘导航时显示） */
:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* 文本框不需要焦点轮廓（已有包装器样式） */
textarea:focus-visible { outline: none; }


/* ========== 引用来源样式（新增） ========== */
.citations {
  margin-top: 12px;
  padding: 12px 14px;
  background: rgba(0, 130, 150, 0.06);
  border-left: 3px solid var(--primary);
  border-radius: 8px;
  font-size: 0.85rem;
  align-self: flex-start;
  max-width: 100%;
}

.theme-dark .citations {
  background: rgba(53, 183, 214, 0.08);
}

.citations-title {
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 8px;
  font-size: 0.85rem;
}

.citations-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.citation-item {
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: background 0.15s;
  line-height: 1.5;
}

.citation-item:hover {
  background: rgba(0, 130, 150, 0.08);
}

.citation-item strong {
  color: var(--primary);
  margin-right: 2px;
}

.citation-detail {
  margin-top: 6px;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 0.8rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.theme-dark .citation-detail {
  background: rgba(255, 255, 255, 0.03);
}

/* 引用区域和消息内容同列（不是横跨整行） */
.message.assistant {
  align-items: flex-start;
}

.message.assistant > .citations {
  /* 让引用挂在消息头像右侧，而不是 message-content 内部 */
  margin-left: 50px;
}

/* ========== 流式渲染样式（新增） ========== */
/* 流式期间用 textContent 填充，保留换行；结束后移除该类并渲染 Markdown */
.message-content.streaming-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
```

---

## 3. js/main.js - 应用主入口

```javascript
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
```

---

## 4. js/api.js - API 客户端

```javascript
// ==================== 文件说明 ====================
// 这是前端 API 客户端模块，负责与后端服务器通信
// 提供三个主要功能：
// 1. chatStream: 流式聊天（实时返回 token / cached_answer / citations / error）
// 2. chat: 非流式聊天（一次性返回完整结果）
// 3. uploadFile: 文件上传（带进度监听）
//
// 本版关键变化：
// chatStream 现在解析并回调四类 SSE 事件：
// - {"token": "..."}          -> onToken
// - {"cached_answer": "..."}  -> onCachedAnswer
// - {"citations": {...}}      -> onCitations
// - {"error": "..."}          -> onError

export const API = {
  // ==================== 流式聊天函数 ====================
  /**
   * 发送流式聊天请求（实时接收响应）
   *
   * @param {string} query - 用户输入的查询文本
   * @param {Object} options - 回调函数配置
   * @param {Function} options.onToken - 收到 token 时的回调
   * @param {Function} options.onCachedAnswer - 缓存命中时的回调（参数：完整答案字符串）
   * @param {Function} options.onCitations - 收到引用时的回调（参数：citation_map 对象）
   * @param {Function} options.onDone - 完成时的回调
   * @param {Function} options.onError - 出错时的回调
   * @returns {Function} - 取消函数，调用后可中断请求
   */
  chatStream(query, { onToken, onCachedAnswer, onCitations, onDone, onError }) {
    let controller = new AbortController();
    let signal = controller.signal;
    let timeoutId;

    const start = () => {
      (async () => {
        try {
          const resp = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
            signal,
          });

          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

          const reader = resp.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const resetTimeout = () => {
            if (timeoutId) clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
              controller.abort();
              onError && onError(new Error('响应超时，请重试'));
            }, 180000);
          };
          resetTimeout();

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const frames = buffer.split('\n\n');
            buffer = frames.pop() || '';

            for (const frame of frames) {
              const lines = frame.split('\n');
              for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                const data = line.slice(6).trim();

                if (data === '[DONE]') {
                  if (timeoutId) clearTimeout(timeoutId);
                  onDone && onDone();
                  return;
                }

                let parsed;
                try {
                  parsed = JSON.parse(data);
                } catch (e) {
                  continue;
                }

                // 分支处理各类事件
                if (parsed.token) {
                  onToken && onToken(parsed.token);
                  resetTimeout();
                } else if (parsed.cached_answer) {
                  onCachedAnswer && onCachedAnswer(parsed.cached_answer);
                  resetTimeout();
                } else if (parsed.citations) {
                  onCitations && onCitations(parsed.citations);
                } else if (parsed.error) {
                  if (timeoutId) clearTimeout(timeoutId);
                  onError && onError(new Error(parsed.error));
                  return;
                }
              }
            }
          }

          // 读完了还没收到 [DONE]，走 onDone 兜底
          if (timeoutId) clearTimeout(timeoutId);
          onDone && onDone();

        } catch (err) {
          if (timeoutId) clearTimeout(timeoutId);
          if (err.name === 'AbortError') return;
          onError && onError(err);
        }
      })();
    };

    start();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      controller.abort();
    };
  },

  // ==================== 非流式聊天函数 ====================
  async chat(query, history = []) {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, history }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    return await resp.json();
  },

  // ==================== 文件上传函数 ====================
  uploadFile(file, { onStatus, onProgress }) {
    const controller = new AbortController();
    const signal = controller.signal;

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.responseType = 'json';

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener('load', async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = xhr.response;

        if (data && data.task_id) {
          onProgress && onProgress(-1);
          const taskId = data.task_id;
          const totalTimeout = 300000;
          const startTime = Date.now();

          while (true) {
            if (Date.now() - startTime > totalTimeout) {
              onStatus && onStatus({ status: 'error', message: '处理超时' });
              return;
            }

            try {
              const taskResp = await fetch(`/task/${taskId}`, { signal });
              const taskData = await taskResp.json();

              if (taskData.status === 'completed') {
                onProgress && onProgress(100);
                onStatus && onStatus({
                  status: 'done',
                  chunks: taskData.chunks_stored,
                  fileName: file.name
                });
                return;
              } else if (taskData.status === 'failed') {
                onStatus && onStatus({
                  status: 'error',
                  message: taskData.message || '处理失败'
                });
                return;
              }
            } catch (err) {
              if (err.name === 'AbortError') return;
            }

            await new Promise(r => setTimeout(r, 1000));
          }
        } else {
          onStatus && onStatus({ status: 'error', message: '无效的响应' });
        }
      } else if (xhr.status === 413) {
        onStatus && onStatus({ status: 'error', message: '文件太大，超过 50MB 限制' });
      } else {
        onStatus && onStatus({ status: 'error', message: `上传失败 (${xhr.status})` });
      }
    });

    xhr.addEventListener('error', () => {
      onStatus && onStatus({ status: 'error', message: '网络错误' });
    });

    xhr.addEventListener('abort', () => {});

    const form = new FormData();
    form.append('file', file);
    xhr.send(form);

    return () => {
      xhr.abort();
      controller.abort();
    };
  }
};
```

---

## 5. js/store.js - 状态管理

```javascript
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
```

---

## 6. js/renderer.js - DOM 渲染

```javascript
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
```

---

## 7. js/utils.js - 工具函数

```javascript
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
```
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
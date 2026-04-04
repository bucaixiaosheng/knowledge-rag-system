/**
 * 知识管理系统 - 前端JavaScript
 * 四大模块：对话检索、混合搜索、图谱查询、文档管理
 */

const API_BASE = 'http://localhost:8100/api/v1';

// ==================== 标签页切换 ====================

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`${tab.dataset.tab}-panel`).classList.add('active');
    });
});

// ==================== 通用工具函数 ====================

/**
 * 简单的Markdown渲染（支持标题、加粗、斜体、代码块、列表、链接）
 */
function renderMarkdown(text) {
    if (!text) return '';
    let html = text
        // 转义HTML特殊字符
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // 代码块 (```...```)
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
        // 行内代码 (`...`)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // 标题
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        // 加粗和斜体
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // 链接
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // 无序列表
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        // 有序列表
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // 换行
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    return `<p>${html}</p>`;
}

/**
 * 显示加载状态
 */
function setLoading(elementId, loading) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (loading) {
        el.dataset.originalContent = el.innerHTML;
        el.innerHTML = '<div class="loading">⏳ 加载中...</div>';
    } else if (el.dataset.originalContent !== undefined) {
        // 仅在仍是loading状态时恢复（避免覆盖已更新的结果）
        if (el.innerHTML.includes('加载中')) {
            delete el.dataset.originalContent;
        }
    }
}

/**
 * 统一的错误处理
 */
function handleError(error, elementId) {
    console.error('API请求失败:', error);
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = `<div class="error">❌ 请求失败: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 对话模块 ====================

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSendBtn = document.getElementById('chat-send');

/**
 * 添加消息到对话区域
 */
function addMessage(role, content, extra = '') {
    const div = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    // 对assistant消息使用Markdown渲染
    if (role === 'assistant') {
        contentDiv.innerHTML = renderMarkdown(content);
    } else {
        contentDiv.textContent = content;
    }
    msgDiv.appendChild(contentDiv);

    if (extra) {
        const extraDiv = document.createElement('div');
        extraDiv.className = 'sources';
        extraDiv.innerHTML = extra;
        msgDiv.appendChild(extraDiv);
    }

    div.appendChild(msgDiv);
    div.scrollTop = div.scrollHeight;
}

/**
 * 发送对话消息
 */
chatSendBtn.addEventListener('click', async () => {
    const query = chatInput.value.trim();
    if (!query) return;

    addMessage('user', query);
    chatInput.value = '';

    // 添加加载指示
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.id = 'chat-loading';
    loadingDiv.innerHTML = '<div>⏳ 思考中...</div>';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const resp = await fetch(`${API_BASE}/chat/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query})
        });

        // 移除加载指示
        const loadEl = document.getElementById('chat-loading');
        if (loadEl) loadEl.remove();

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();

        // 渲染来源信息
        let sourcesHtml = '';
        if (data.sources && data.sources.length > 0) {
            sourcesHtml = data.sources.map(s =>
                `📄 ${escapeHtml(s.title || s.doc_id)} (相关度: ${((s.score || 0) * 100).toFixed(0)}%)`
            ).join('<br>');
            sourcesHtml = `<b>参考来源 (${data.context_count || data.sources.length}条):</b><br>` + sourcesHtml;
        }

        addMessage('assistant', data.answer, sourcesHtml);
    } catch (e) {
        const loadEl = document.getElementById('chat-loading');
        if (loadEl) loadEl.remove();
        addMessage('assistant', '❌ 请求失败: ' + e.message);
    }
});

// 回车发送（Shift+Enter换行）
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatSendBtn.click();
    }
});

// ==================== 混合搜索模块 ====================

document.getElementById('search-btn').addEventListener('click', async () => {
    const query = document.getElementById('search-query').value.trim();
    if (!query) return;

    const vw = parseFloat(document.getElementById('vec-weight').value);
    const gw = parseFloat(document.getElementById('graph-weight').value);
    const kw = parseFloat(document.getElementById('kw-weight').value);

    const resultsDiv = document.getElementById('search-results');
    setLoading('search-results', true);

    try {
        const resp = await fetch(`${API_BASE}/search/hybrid`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query,
                vector_weight: vw,
                graph_weight: gw,
                keyword_weight: kw
            })
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();

        if (!data.results || data.results.length === 0) {
            resultsDiv.innerHTML = '<div class="no-results">未找到相关结果</div>';
            return;
        }

        resultsDiv.innerHTML = data.results.map(r => {
            const score = ((r.score || 0) * 100).toFixed(0);
            const highlighted = highlightKeywords(r.content, query);
            return `<div class="result-item">
                <div class="score">相关度: ${score}% | 来源: ${escapeHtml(r.source || '未知')}</div>
                <div>${highlighted}</div>
                <div class="source">文档: ${escapeHtml(r.doc_id || '未知')} | Chunk: ${escapeHtml(r.chunk_id || '')}</div>
            </div>`;
        }).join('');
    } catch (e) {
        handleError(e, 'search-results');
    }
});

/**
 * 关键词高亮
 */
function highlightKeywords(content, query) {
    if (!content || !query) return escapeHtml(content || '');
    const escaped = escapeHtml(content);
    const keywords = query.split(/\s+/).filter(k => k.length > 0);
    let result = escaped;
    keywords.forEach(kw => {
        const regex = new RegExp(`(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        result = result.replace(regex, '<mark>$1</mark>');
    });
    return result;
}

// 滑块值实时更新
['vec', 'graph', 'kw'].forEach(prefix => {
    const slider = document.getElementById(`${prefix}-weight`);
    const display = document.getElementById(`${prefix}-val`);
    if (slider && display) {
        slider.addEventListener('input', e => {
            display.textContent = e.target.value;
        });
    }
});

// 搜索框回车触发搜索
document.getElementById('search-query').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('search-btn').click();
    }
});

// ==================== 图谱查询模块 ====================

// 图谱搜索
document.getElementById('graph-search-btn').addEventListener('click', async () => {
    const keyword = document.getElementById('graph-keyword').value.trim();
    if (!keyword) return;

    setLoading('graph-results', true);

    try {
        const resp = await fetch(`${API_BASE}/graph/search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({keyword})
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        const resultsDiv = document.getElementById('graph-results');

        if (!data.results || data.results.length === 0) {
            resultsDiv.innerHTML = '<div class="no-results">未找到相关图谱节点</div>';
            return;
        }

        resultsDiv.innerHTML = data.results.map(r =>
            `<div class="result-item">
                <strong>${escapeHtml(r.title || r.name || '未知')}</strong>
                (score: ${(r.score || 0).toFixed(2)})
                <p>${escapeHtml(r.summary || r.content || '')}</p>
            </div>`
        ).join('');
    } catch (e) {
        handleError(e, 'graph-results');
    }
});

// 图谱统计信息
document.getElementById('graph-stats-btn').addEventListener('click', async () => {
    setLoading('graph-results', true);

    try {
        const resp = await fetch(`${API_BASE}/graph/stats`);
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const data = await resp.json();
        document.getElementById('graph-results').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (e) {
        handleError(e, 'graph-results');
    }
});

// 图谱搜索框回车
document.getElementById('graph-keyword').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('graph-search-btn').click();
    }
});

// ==================== 文档管理模块 ====================

// 文件上传
document.getElementById('upload-btn').addEventListener('click', async () => {
    const fileInput = document.getElementById('file-input');
    if (!fileInput.files || !fileInput.files[0]) {
        document.getElementById('upload-status').textContent = '⚠️ 请先选择文件';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const statusEl = document.getElementById('upload-status');
    statusEl.textContent = '⏳ 上传中...';
    statusEl.className = '';

    try {
        const resp = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            body: formData
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        statusEl.textContent = `✅ ${data.status}: ${data.title || data.doc_id} (${data.chunk_count || 0} chunks)`;
        fileInput.value = ''; // 清空文件选择
    } catch (e) {
        statusEl.textContent = `❌ 上传失败: ${e.message}`;
    }
});

// URL入库
document.getElementById('url-ingest-btn').addEventListener('click', async () => {
    const url = document.getElementById('url-input').value.trim();
    if (!url) {
        alert('请输入URL');
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/documents/url`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url})
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${resp.status}`);
        }

        const data = await resp.json();
        alert(`入库${data.status}: ${data.title || data.doc_id}`);
        document.getElementById('url-input').value = ''; // 清空输入
    } catch (e) {
        alert('入库失败: ' + e.message);
    }
});

// 统计信息
document.getElementById('stats-btn').addEventListener('click', async () => {
    const statsDiv = document.getElementById('stats-results');
    statsDiv.innerHTML = '<div class="loading">⏳ 加载中...</div>';

    try {
        // 并行请求向量库和图谱统计
        const [docsResp, graphResp] = await Promise.allSettled([
            fetch(`${API_BASE}/documents/stats`),
            fetch(`${API_BASE}/graph/stats`)
        ]);

        let html = '';

        // 文档统计
        if (docsResp.status === 'fulfilled' && docsResp.value.ok) {
            const docStats = await docsResp.value.json();
            html += '<h4>📊 文档统计</h4>';
            html += `<pre>${JSON.stringify(docStats, null, 2)}</pre>`;
        } else {
            html += '<h4>📊 文档统计</h4><p>❌ 获取失败</p>';
        }

        // 图谱统计
        if (graphResp.status === 'fulfilled' && graphResp.value.ok) {
            const graphStats = await graphResp.value.json();
            html += '<h4>🕸️ 图谱统计</h4>';
            html += `<pre>${JSON.stringify(graphStats, null, 2)}</pre>`;
        } else {
            html += '<h4>🕸️ 图谱统计</h4><p>❌ 获取失败</p>';
        }

        statsDiv.innerHTML = html;
    } catch (e) {
        statsDiv.innerHTML = `<div class="error">❌ 获取统计信息失败: ${escapeHtml(e.message)}</div>`;
    }
});

"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatViewProvider = void 0;
const vscode = require("vscode");
const http = require("http");
const https = require("https");
const path = require("path");
class ChatViewProvider {
    constructor(_context) {
        this._context = _context;
        this._history = [];
        this._abortController = null;
        // Tracks the model selected in the UI dropdown (overrides VS Code settings)
        this._selectedModel = null;
        // Track last file paths for auto-opening
        this._lastEditFilePath = null;
        this._lastCreateFilePath = null;
    }
    resolveWebviewView(webviewView) {
        this._view = webviewView;
        webviewView.webview.options = { enableScripts: true };
        webviewView.webview.html = this._getHtml();
        webviewView.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.type) {
                case 'send':
                    await this._handleUserMessage(msg.text);
                    break;
                case 'cancel':
                    this._abortController?.abort();
                    break;
                case 'clear':
                    this.clearChat();
                    break;
                case 'openFile':
                    await this._openFile(msg.filePath);
                    break;
                case 'showDiff':
                    await this._showDiff(msg.filePath, msg.oldContent, msg.newContent);
                    break;
                case 'getModels':
                    await this._fetchAndSendModels();
                    break;
                // ── FIX 1: listen for model selection changes ──
                case 'modelChanged':
                    this._selectedModel = msg.model;
                    break;
                // ── FIX 2: restore history from persisted webview state ──
                case 'restoreHistory':
                    // History was restored from vscode.getState() in the webview;
                    // sync our in-memory history array with what the webview knows.
                    if (Array.isArray(msg.history)) {
                        this._history = msg.history;
                    }
                    break;
            }
        });
    }
    clearChat() {
        this._history = [];
        this._abortController?.abort();
        this._view?.webview.postMessage({ type: 'clear' });
    }
    _getConfig() {
        const cfg = vscode.workspace.getConfiguration('codeAgent');
        return {
            backendUrl: cfg.get('backendUrl', 'http://127.0.0.1:8765'),
            model: cfg.get('model', 'gemma4:12b'),
            confirmFileEdits: cfg.get('confirmFileEdits', false),
            confirmFileDeletion: cfg.get('confirmFileDeletion', true),
            confirmDangerousCommands: cfg.get('confirmDangerousCommands', true),
        };
    }
    /** Returns the effective model: UI selection > VS Code setting > hardcoded default */
    _getEffectiveModel() {
        if (this._selectedModel) {
            return this._selectedModel;
        }
        return this._getConfig().model;
    }
    _getWorkspace() {
        const folders = vscode.workspace.workspaceFolders;
        if (!folders || folders.length === 0) {
            throw new Error('No workspace folder open. Please open a folder first.');
        }
        return folders[0].uri.fsPath;
    }
    async _fetchAndSendModels() {
        const { backendUrl } = this._getConfig();
        try {
            const data = await this._httpGet(`${backendUrl}/models`);
            const parsed = JSON.parse(data);
            const models = parsed.models || [];
            // Pre-select the currently effective model in the dropdown
            this._view?.webview.postMessage({
                type: 'models',
                models,
                selectedModel: this._getEffectiveModel(),
            });
        }
        catch {
            this._view?.webview.postMessage({ type: 'models', models: [], selectedModel: '' });
        }
    }
    _httpGet(url) {
        return new Promise((resolve, reject) => {
            const lib = url.startsWith('https') ? https : http;
            lib.get(url, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => resolve(data));
            }).on('error', reject);
        });
    }
    async _handleUserMessage(text) {
        const cfg = this._getConfig();
        // ── FIX 1: use the UI-selected model, not always the VS Code setting ──
        const model = this._getEffectiveModel();
        let workspace;
        try {
            workspace = this._getWorkspace();
        }
        catch (e) {
            this._view?.webview.postMessage({ type: 'error', message: e.message });
            return;
        }
        this._view?.webview.postMessage({ type: 'userMessage', text });
        this._view?.webview.postMessage({ type: 'agentStart' });
        this._abortController = new AbortController();
        const body = JSON.stringify({
            workspace,
            message: text,
            history: this._history,
            model,
            settings: {
                confirmFileEdits: cfg.confirmFileEdits,
                confirmFileDeletion: cfg.confirmFileDeletion,
                confirmDangerousCommands: cfg.confirmDangerousCommands,
            },
        });
        const url = new URL(`${cfg.backendUrl}/chat`);
        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body),
            },
        };
        const lib = url.protocol === 'https:' ? https : http;
        const req = lib.request(options, (res) => {
            let buffer = '';
            res.on('data', (chunk) => {
                buffer += chunk.toString();
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (!line.startsWith('data: '))
                        continue;
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') {
                        this._view?.webview.postMessage({ type: 'agentDone' });
                        return;
                    }
                    try {
                        const event = JSON.parse(data);
                        this._handleAgentEvent(event, text);
                    }
                    catch { }
                }
            });
            res.on('end', () => {
                this._view?.webview.postMessage({ type: 'agentDone' });
            });
        });
        req.on('error', (e) => {
            this._view?.webview.postMessage({
                type: 'error',
                message: `Cannot connect to backend at ${cfg.backendUrl}. Is the server running?\n\nStart it with: python run_server.py`,
            });
        });
        this._abortController.signal.addEventListener('abort', () => {
            req.destroy();
            this._view?.webview.postMessage({ type: 'agentDone' });
        });
        req.write(body);
        req.end();
    }
    _handleAgentEvent(event, userText) {
        switch (event.type) {
            case 'model_info':
                // Show which model is being used in the log
                this._view?.webview.postMessage({ type: 'modelInfo', model: event.model });
                break;
            case 'tool_call':
                this._view?.webview.postMessage({ type: 'toolCall', tool: event.tool, args: event.args });
                break;
            case 'tool_result':
                this._view?.webview.postMessage({ type: 'toolResult', tool: event.tool, result: event.result });
                // Auto-open modified files in editor
                if ((event.tool === 'edit_file' || event.tool === 'create_file') && !event.result.startsWith('ERROR')) {
                    const workspace = this._getWorkspaceSafe();
                    if (workspace) {
                        const filePath = event.tool === 'edit_file'
                            ? this._lastEditFilePath
                            : this._lastCreateFilePath;
                        if (filePath) {
                            const fullPath = path.join(workspace, filePath);
                            vscode.workspace.openTextDocument(fullPath).then(doc => {
                                vscode.window.showTextDocument(doc, { preview: true, preserveFocus: true });
                            });
                        }
                    }
                }
                break;
            case 'done':
                this._history.push({ role: 'user', content: userText });
                this._history.push({ role: 'assistant', content: event.content });
                // Keep history manageable
                if (this._history.length > 40) {
                    this._history = this._history.slice(-40);
                }
                this._view?.webview.postMessage({ type: 'agentMessage', content: event.content });
                break;
            case 'error':
                this._view?.webview.postMessage({ type: 'error', message: event.message });
                break;
        }
    }
    _getWorkspaceSafe() {
        try {
            return this._getWorkspace();
        }
        catch {
            return null;
        }
    }
    async _openFile(filePath) {
        const workspace = this._getWorkspaceSafe();
        if (!workspace)
            return;
        const fullPath = path.join(workspace, filePath);
        try {
            const doc = await vscode.workspace.openTextDocument(fullPath);
            await vscode.window.showTextDocument(doc);
        }
        catch (e) {
            vscode.window.showErrorMessage(`Cannot open file: ${e.message}`);
        }
    }
    async _showDiff(filePath, oldContent, newContent) {
        const oldUri = vscode.Uri.parse(`untitled:${filePath} (before)`);
        const newUri = vscode.Uri.parse(`untitled:${filePath} (after)`);
        await vscode.commands.executeCommand('vscode.diff', oldUri, newUri, `Diff: ${filePath}`);
    }
    _getHtml() {
        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Code Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-sideBar-background);
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }
  #toolbar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    border-bottom: 1px solid var(--vscode-panel-border);
    flex-shrink: 0;
  }
  #model-select {
    flex: 1;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border);
    padding: 3px 6px;
    border-radius: 3px;
    font-size: 11px;
  }
  .toolbar-btn {
    background: none;
    border: none;
    color: var(--vscode-foreground);
    cursor: pointer;
    padding: 3px 6px;
    border-radius: 3px;
    font-size: 11px;
    opacity: 0.7;
  }
  .toolbar-btn:hover { opacity: 1; background: var(--vscode-toolbar-hoverBackground); }
  #messages {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .msg {
    padding: 8px 10px;
    border-radius: 6px;
    line-height: 1.5;
    word-break: break-word;
  }
  .msg-user {
    background: var(--vscode-input-background);
    border-left: 3px solid var(--vscode-focusBorder);
    align-self: flex-end;
    max-width: 90%;
  }
  .msg-agent {
    background: var(--vscode-editor-background);
    border-left: 3px solid var(--vscode-activityBarBadge-background);
    white-space: pre-wrap;
  }
  .msg-error {
    background: var(--vscode-inputValidation-errorBackground);
    border-left: 3px solid var(--vscode-inputValidation-errorBorder);
    white-space: pre-wrap;
  }
  .msg-model-info {
    font-size: 10px;
    opacity: 0.55;
    text-align: center;
    padding: 2px 0;
    font-style: italic;
  }
  .tool-block {
    background: var(--vscode-editor-background);
    border: 1px solid var(--vscode-panel-border);
    border-radius: 4px;
    overflow: hidden;
    font-size: 11px;
  }
  .tool-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: var(--vscode-sideBarSectionHeader-background);
    cursor: pointer;
    user-select: none;
  }
  .tool-header:hover { background: var(--vscode-list-hoverBackground); }
  .tool-name { font-weight: bold; flex: 1; }
  .tool-status { font-size: 10px; opacity: 0.7; }
  .tool-body {
    padding: 6px 8px;
    display: none;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    font-family: var(--vscode-editor-font-family);
    font-size: 11px;
    color: var(--vscode-editor-foreground);
  }
  .tool-body.expanded { display: block; }
  .tool-icon { font-size: 13px; }
  .thinking {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    opacity: 0.7;
    font-style: italic;
  }
  .spinner {
    width: 14px; height: 14px;
    border: 2px solid var(--vscode-foreground);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  #input-area {
    padding: 8px;
    border-top: 1px solid var(--vscode-panel-border);
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex-shrink: 0;
  }
  #input {
    width: 100%;
    min-height: 60px;
    max-height: 150px;
    resize: vertical;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border);
    padding: 6px 8px;
    border-radius: 4px;
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
  }
  #input:focus { outline: 1px solid var(--vscode-focusBorder); }
  .btn-row { display: flex; gap: 6px; }
  #send-btn {
    flex: 1;
    padding: 6px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
  }
  #send-btn:hover { background: var(--vscode-button-hoverBackground); }
  #send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  #cancel-btn {
    padding: 6px 10px;
    background: var(--vscode-button-secondaryBackground);
    color: var(--vscode-button-secondaryForeground);
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    display: none;
  }
  #cancel-btn:hover { background: var(--vscode-button-secondaryHoverBackground); }
  #cancel-btn.visible { display: block; }
  .hint { font-size: 10px; opacity: 0.5; text-align: center; }
  code { font-family: var(--vscode-editor-font-family); background: var(--vscode-textCodeBlock-background); padding: 1px 4px; border-radius: 3px; }
</style>
</head>
<body>
<div id="toolbar">
  <select id="model-select" title="Ollama model"></select>
  <button class="toolbar-btn" onclick="clearChat()" title="Clear chat">🗑</button>
</div>
<div id="messages">
  <div class="hint">Open a workspace folder, then ask the agent anything about your code.</div>
</div>
<div id="input-area">
  <textarea id="input" placeholder="Ask the agent to read, edit, create files, run commands..." rows="3"></textarea>
  <div class="btn-row">
    <button id="send-btn" onclick="sendMessage()">Send (Ctrl+Enter)</button>
    <button id="cancel-btn" onclick="cancelAgent()">⏹ Stop</button>
  </div>
</div>

<script>
const vscode = acquireVsCodeApi();
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send-btn');
const cancelBtn = document.getElementById('cancel-btn');
const modelSelect = document.getElementById('model-select');

let isRunning = false;
let currentAgentBlock = null;
let thinkingEl = null;

// ── FIX 2: Restore chat UI from persisted state on panel re-open ──
(function restoreState() {
  const state = vscode.getState();
  if (state && state.messages && state.messages.length > 0) {
    messagesEl.innerHTML = '';
    for (const m of state.messages) {
      restoreMessage(m);
    }
    scrollToBottom();
    // Sync history back to the extension host
    if (state.history) {
      vscode.postMessage({ type: 'restoreHistory', history: state.history });
    }
  }
  if (state && state.selectedModel) {
    // We'll apply this after models load
    window._pendingSelectedModel = state.selectedModel;
  }
})();

// Persist state whenever we add messages
let _persistedMessages = [];
let _persistedHistory = [];

function persistState() {
  vscode.setState({ messages: _persistedMessages, history: _persistedHistory, selectedModel: modelSelect.value });
}

function restoreMessage(m) {
  if (m.type === 'user') {
    const div = document.createElement('div');
    div.className = 'msg msg-user';
    div.textContent = m.text;
    messagesEl.appendChild(div);
  } else if (m.type === 'agent') {
    const div = document.createElement('div');
    div.className = 'msg msg-agent';
    div.textContent = m.content;
    messagesEl.appendChild(div);
  } else if (m.type === 'error') {
    const div = document.createElement('div');
    div.className = 'msg msg-error';
    div.textContent = m.text;
    messagesEl.appendChild(div);
  } else if (m.type === 'modelInfo') {
    const div = document.createElement('div');
    div.className = 'msg-model-info';
    div.textContent = m.text;
    messagesEl.appendChild(div);
  } else if (m.type === 'tool') {
    // Restore collapsed tool blocks
    const block = document.createElement('div');
    block.className = 'tool-block';
    block.innerHTML = \`
      <div class="tool-header" onclick="toggleTool(this)">
        <span class="tool-icon">\${m.icon}</span>
        <span class="tool-name">\${m.tool}</span>
        <span class="tool-status">\${m.status}</span>
        <span class="chevron">▶</span>
      </div>
      <div class="tool-body">\${escapeHtml(m.result || '')}</div>
    \`;
    messagesEl.appendChild(block);
  }
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Request models on load
vscode.postMessage({ type: 'getModels' });

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ── FIX 1: Store selected model and notify extension host ──
modelSelect.addEventListener('change', () => {
  vscode.postMessage({ type: 'modelChanged', model: modelSelect.value });
  persistState();
});

function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isRunning) return;
  inputEl.value = '';
  vscode.postMessage({ type: 'send', text });
}

function cancelAgent() {
  vscode.postMessage({ type: 'cancel' });
}

function clearChat() {
  _persistedMessages = [];
  _persistedHistory = [];
  persistState();
  vscode.postMessage({ type: 'clear' });
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addMessage(cls, content) {
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = content;
  messagesEl.appendChild(div);
  scrollToBottom();
  return div;
}

function toolIcon(tool) {
  const icons = {
    list_files: '📁', read_file: '📖', search_code: '🔍',
    create_file: '✨', edit_file: '✏️', delete_file: '🗑️',
    run_command: '▶️', get_file_info: 'ℹ️', run_tests: '🧪',
  };
  return icons[tool] || '🔧';
}

function addToolBlock(tool, args) {
  const block = document.createElement('div');
  block.className = 'tool-block';

  const argsStr = Object.entries(args || {})
    .map(([k, v]) => {
      const val = typeof v === 'string' && v.length > 80 ? v.slice(0, 80) + '...' : v;
      return k + ': ' + val;
    })
    .join('  ');

  const icon = toolIcon(tool);
  block.innerHTML = \`
    <div class="tool-header" onclick="toggleTool(this)">
      <span class="tool-icon">\${icon}</span>
      <span class="tool-name">\${tool}</span>
      <span class="tool-status running">\${argsStr}</span>
      <span class="chevron">▶</span>
    </div>
    <div class="tool-body"></div>
  \`;

  block.dataset.tool = tool;
  block.dataset.icon = icon;
  block.dataset.args = argsStr;

  messagesEl.appendChild(block);
  scrollToBottom();
  return block;
}

function toggleTool(header) {
  const body = header.nextElementSibling;
  body.classList.toggle('expanded');
  header.querySelector('.chevron').textContent = body.classList.contains('expanded') ? '▼' : '▶';
}

function setToolResult(block, result, success) {
  const status = block.querySelector('.tool-status');
  const body = block.querySelector('.tool-body');
  const statusText = success ? '✅' : '❌';
  status.textContent = statusText;
  body.textContent = result;

  // Update persisted messages: find this block's persisted entry and update it
  const idx = Array.from(messagesEl.children).indexOf(block);
  if (idx >= 0 && _persistedMessages[idx] && _persistedMessages[idx].type === 'tool') {
    _persistedMessages[idx].status = statusText;
    _persistedMessages[idx].result = result;
    persistState();
  }
}

window.addEventListener('message', (event) => {
  const msg = event.data;

  switch (msg.type) {
    case 'userMessage':
      addMessage('msg-user', msg.text);
      _persistedMessages.push({ type: 'user', text: msg.text });
      persistState();
      break;

    case 'modelInfo':
      // Show which model the agent is actually using
      {
        const div = document.createElement('div');
        div.className = 'msg-model-info';
        div.textContent = \`🤖 Using model: \${msg.model}\`;
        messagesEl.appendChild(div);
        scrollToBottom();
        _persistedMessages.push({ type: 'modelInfo', text: \`🤖 Using model: \${msg.model}\` });
        persistState();
      }
      break;

    case 'agentStart':
      isRunning = true;
      sendBtn.disabled = true;
      cancelBtn.classList.add('visible');
      currentAgentBlock = null;
      thinkingEl = document.createElement('div');
      thinkingEl.className = 'thinking';
      thinkingEl.innerHTML = '<div class="spinner"></div><span>Agent is working...</span>';
      messagesEl.appendChild(thinkingEl);
      scrollToBottom();
      break;

    case 'toolCall':
      if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
      currentAgentBlock = addToolBlock(msg.tool, msg.args);
      // Push a placeholder for this tool call into persisted messages
      _persistedMessages.push({
        type: 'tool',
        tool: msg.tool,
        icon: toolIcon(msg.tool),
        args: currentAgentBlock.dataset.args,
        status: '⏳',
        result: '',
      });
      persistState();
      // Track file paths for auto-open
      if (msg.tool === 'edit_file' && msg.args.file_path) {
        window._lastEditPath = msg.args.file_path;
      }
      if (msg.tool === 'create_file' && msg.args.file_path) {
        window._lastCreatePath = msg.args.file_path;
      }
      break;

    case 'toolResult':
      if (currentAgentBlock) {
        const success = !msg.result.startsWith('ERROR') && !msg.result.startsWith('BLOCKED');
        setToolResult(currentAgentBlock, msg.result, success);
        currentAgentBlock = null;
      }
      // Show thinking again while agent processes result
      thinkingEl = document.createElement('div');
      thinkingEl.className = 'thinking';
      thinkingEl.innerHTML = '<div class="spinner"></div><span>Processing...</span>';
      messagesEl.appendChild(thinkingEl);
      scrollToBottom();
      break;

    case 'agentMessage':
      if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
      addMessage('msg-agent', msg.content);
      _persistedMessages.push({ type: 'agent', content: msg.content });
      persistState();
      break;

    case 'agentDone':
      if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
      isRunning = false;
      sendBtn.disabled = false;
      cancelBtn.classList.remove('visible');
      break;

    case 'error':
      if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
      addMessage('msg-error', '⚠️ ' + msg.message);
      _persistedMessages.push({ type: 'error', text: '⚠️ ' + msg.message });
      persistState();
      isRunning = false;
      sendBtn.disabled = false;
      cancelBtn.classList.remove('visible');
      break;

    case 'clear':
      messagesEl.innerHTML = '<div class="hint">Chat cleared. Ask the agent anything about your code.</div>';
      _persistedMessages = [];
      _persistedHistory = [];
      persistState();
      isRunning = false;
      sendBtn.disabled = false;
      cancelBtn.classList.remove('visible');
      break;

    case 'models':
      modelSelect.innerHTML = '';
      if (msg.models.length === 0) {
        const opt = document.createElement('option');
        opt.value = 'gemma4:12b';
        opt.textContent = 'gemma4:12b (default)';
        modelSelect.appendChild(opt);
      } else {
        msg.models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m;
          opt.textContent = m;
          modelSelect.appendChild(opt);
        });
        // ── FIX 1: restore previously selected model in dropdown ──
        const target = window._pendingSelectedModel || msg.selectedModel;
        if (target) {
          modelSelect.value = target;
          // If the value was set successfully, notify extension host
          if (modelSelect.value === target) {
            vscode.postMessage({ type: 'modelChanged', model: target });
          }
        }
      }
      break;
  }
});

// Sync history after agent message
window.addEventListener('message', (event) => {
  // Mirror history for persistence whenever agentMessage arrives
  // (done event carries content, which already got pushed by agentMessage above)
});
</script>
</body>
</html>`;
    }
}
exports.ChatViewProvider = ChatViewProvider;
//# sourceMappingURL=chatViewProvider.js.map
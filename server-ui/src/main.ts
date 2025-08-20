import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

interface ServerStatus {
  running: boolean;
  pid?: number;
  port?: number;
}

interface ServerConfig {
  working_directory?: string;
  default_port: number;
}

interface ServerOutput {
  timestamp: string;
  stream: string; // "stdout" or "stderr"
  content: string;
}

interface EnvVariable {
  key: string;
  value: string;
  comment?: string;
}

type EnvVariables = EnvVariable[];

let serverStatus: ServerStatus = { running: false };
let serverConfig: ServerConfig = { default_port: 8000 };
let serverReady: boolean = false; // Track if Uvicorn startup log has been seen
let envVariables: EnvVariables = [];
let statusEl: HTMLElement | null;
let statusTextEl: HTMLElement | null;
let startBtn: HTMLElement | null;
let stopBtn: HTMLElement | null;
let restartBtn: HTMLElement | null;
let tabHeaders: NodeListOf<HTMLElement> | null;
let portInput: HTMLInputElement | null;
let logsEl: HTMLElement | null;
let workingDirInput: HTMLInputElement | null;
let browseBtn: HTMLElement | null;
let saveConfigBtn: HTMLElement | null;
let clearLogsBtn: HTMLElement | null;
let envPanel: HTMLElement | null;
let envListEl: HTMLElement | null;

let saveEnvBtn: HTMLElement | null;
let loadEnvBtn: HTMLElement | null;
let envFilePathEl: HTMLElement | null;

async function updateServerStatus() {
  try {
    serverStatus = await invoke("get_server_status");
    updateUI();
  } catch (error) {
    console.error("Failed to get server status:", error);
    addLog(`Error: ${error}`);
  }
}

async function loadServerConfig() {
  try {
    serverConfig = await invoke("get_server_config");
    updateConfigUI();
  } catch (error) {
    console.error("Failed to get server config:", error);
    addLog(`Error loading config: ${error}`);
  }
}

function updateUI() {
  if (statusEl) {
    if (serverStatus.running && !serverReady) {
      statusEl.className = "status starting";
    } else {
      statusEl.className = serverStatus.running ? "status running" : "status stopped";
    }
  }

  if (statusTextEl) {
    if (serverStatus.running && !serverReady) {
      statusTextEl.textContent = `Starting... (PID: ${serverStatus.pid}, Port: ${serverStatus.port})`;
    } else {
      statusTextEl.textContent = serverStatus.running
        ? `Running (PID: ${serverStatus.pid}, Port: ${serverStatus.port})`
        : "Stopped";
    }
  }

  if (startBtn) startBtn.style.display = serverStatus.running ? "none" : "inline-flex";

  // Show stop/restart buttons when server is running, but disable them if not ready
  if (stopBtn) {
    stopBtn.style.display = serverStatus.running ? "inline-flex" : "none";
    if (serverStatus.running) {
      if (serverReady) {
        stopBtn.classList.remove("disabled");
        stopBtn.removeAttribute("disabled");
      } else {
        stopBtn.classList.add("disabled");
        stopBtn.setAttribute("disabled", "true");
      }
    }
  }

  if (restartBtn) {
    restartBtn.style.display = serverStatus.running ? "inline-flex" : "none";
    if (serverStatus.running) {
      if (serverReady) {
        restartBtn.classList.remove("disabled");
        restartBtn.removeAttribute("disabled");
      } else {
        restartBtn.classList.add("disabled");
        restartBtn.setAttribute("disabled", "true");
      }
    }
  }
}

function updateConfigUI() {
  if (portInput) {
    portInput.value = serverConfig.default_port.toString();
  }
  if (workingDirInput) {
    workingDirInput.value = serverConfig.working_directory || "";
  }
}

function addLog(message: string, isServerOutput: boolean = false) {
  if (logsEl) {
    const timestamp = new Date().toLocaleTimeString();
    const className = isServerOutput ? "log-entry server-output" : "log-entry";
    logsEl.innerHTML += `<div class="${className}">[${timestamp}] ${message}</div>`;
    logsEl.scrollTop = logsEl.scrollHeight;
  }
}

function addServerOutput(output: ServerOutput) {
  if (logsEl) {
    const className = output.stream === "stderr" ? "log-entry server-error" : "log-entry server-output";
    const prefix = output.stream === "stderr" ? "[SERVER ERROR]" : "[SERVER]";
    logsEl.innerHTML += `<div class="${className}">[${output.timestamp}] ${prefix} ${output.content}</div>`;
    logsEl.scrollTop = logsEl.scrollHeight;
  }

  // Check if this is the Uvicorn startup log indicating server is ready
  if (output.content.includes("Uvicorn running on http://") && !serverReady) {
    serverReady = true;
    updateUI();
    addLog("Server is ready for connections");
  }
}

async function startServer() {
  try {
    const port = portInput?.value ? parseInt(portInput.value) : serverConfig.default_port;
    addLog(`Starting server on port ${port}...`);

    // Reset server ready state when starting
    serverReady = false;

    serverStatus = await invoke("start_server", { port });
    updateUI();
    addLog(`Server started successfully (PID: ${serverStatus.pid})`);
  } catch (error) {
    console.error("Failed to start server:", error);
    addLog(`Failed to start server: ${error}`);
  }
}

async function stopServer() {
  try {
    addLog("Stopping server...");
    serverStatus = await invoke("stop_server");

    // Reset server ready state when stopping
    serverReady = false;

    updateUI();
    addLog("Server stopped successfully");
  } catch (error) {
    console.error("Failed to stop server:", error);
    addLog(`Failed to stop server: ${error}`);
  }
}

async function restartServer() {
  try {
    const port = portInput?.value ? parseInt(portInput.value) : serverConfig.default_port;
    addLog(`Restarting server on port ${port}...`);

    // Reset server ready state when restarting
    serverReady = false;

    serverStatus = await invoke("restart_server", { port });
    updateUI();
    addLog(`Server restarted successfully (PID: ${serverStatus.pid})`);
  } catch (error) {
    console.error("Failed to restart server:", error);
    addLog(`Failed to restart server: ${error}`);
  }
}

async function browseWorkingDirectory() {
  try {
    const suggestedPath: string | null = await invoke("browse_working_directory");
    if (suggestedPath && workingDirInput) {
      workingDirInput.value = suggestedPath;
      addLog(`Suggested working directory: ${suggestedPath}`);
      addLog("You can edit this path manually or leave empty for auto-detect");
    }
  } catch (error) {
    console.error("Failed to get working directory suggestion:", error);
    addLog(`Failed to get working directory suggestion: ${error}`);
  }
}

async function saveConfig() {
  try {
    const newConfig: ServerConfig = {
      working_directory: workingDirInput?.value || undefined,
      default_port: parseInt(portInput?.value || "8000")
    };

    await invoke("set_server_config", { config: newConfig });
    serverConfig = newConfig;
    addLog("Configuration saved successfully");
  } catch (error) {
    console.error("Failed to save config:", error);
    addLog(`Failed to save config: ${error}`);
  }
}

async function loadEnvFile() {
  try {
    envVariables = await invoke("load_env_file");
    updateEnvUI();
    addLog(`Loaded ${envVariables.length} environment variables`);
  } catch (error) {
    console.error("Failed to load env file:", error);
    addLog(`Failed to load env file: ${error}`);
  }
}

async function saveEnvFile() {
  try {
    await invoke("save_env_file", { variables: envVariables });
    addLog("Environment variables saved successfully");
  } catch (error) {
    console.error("Failed to save env file:", error);
    addLog(`Failed to save env file: ${error}`);
  }
}

async function loadEnvFileRaw() {
  try {
    const content = await invoke<string>("load_env_file_raw");
    updateEnvTextArea(content);
    addLog("Environment file loaded successfully");
  } catch (error) {
    console.error("Failed to load env file:", error);
    addLog(`Failed to load env file: ${error}`);
  }
}

async function saveEnvFileRaw() {
  try {
    const content = getEnvTextAreaContent();
    await invoke("save_env_file_raw", { content });
    addLog("Environment file saved successfully");
  } catch (error) {
    console.error("Failed to save env file:", error);
    addLog(`Failed to save env file: ${error}`);
  }
}

async function getEnvFilePath() {
  try {
    const path = await invoke<string>("get_env_file_path");
    if (envFilePathEl) {
      envFilePathEl.textContent = path;
    }
  } catch (error) {
    console.error("Failed to get env file path:", error);
    addLog(`Failed to get env file path: ${error}`);
  }
}

function addEnvVariable(key?: string, value?: string, comment?: string) {
  const newVar: EnvVariable = {
    key: key || "",
    value: value || "",
    comment: comment || undefined
  };
  envVariables.push(newVar);
  updateEnvUI();
}

function removeEnvVariable(index: number) {
  envVariables.splice(index, 1);
  updateEnvUI();
}

function updateEnvVariable(index: number, field: keyof EnvVariable, value: string) {
  if (field === 'comment') {
    envVariables[index][field] = value || undefined;
  } else {
    envVariables[index][field] = value;
  }
  updateEnvUI();
}

function switchTab(tabName: string) {
  // Update tab headers
  if (tabHeaders) {
    tabHeaders.forEach(header => {
      if (header.dataset.tab === tabName) {
        header.classList.add("active");
      } else {
        header.classList.remove("active");
      }
    });
  }

  // Update tab panels
  const tabPanels = document.querySelectorAll(".tab-panel");
  tabPanels.forEach(panel => {
    if (panel.id === `${tabName}-panel`) {
      panel.classList.add("active");
    } else {
      panel.classList.remove("active");
    }
  });
}

function clearLogs() {
  if (logsEl) {
    logsEl.innerHTML = "";
    addLog("Logs cleared");
  }
}

function updateEnvTextArea(content: string) {
  if (!envListEl) return;

  // Clear existing content
  envListEl.innerHTML = "";

  // Create text area element
  const textArea = document.createElement("textarea");
  textArea.className = "env-textarea";
  textArea.placeholder = "Enter environment variables here...\n\nExample:\n# Database configuration\nDB_HOST=localhost\nDB_PORT=5432\n\n# API Keys\nAPI_KEY=your_key_here";
  textArea.value = content;
  textArea.rows = 20;
  textArea.spellcheck = false;

  // Add to container
  envListEl.appendChild(textArea);
}

function getEnvTextAreaContent(): string {
  if (!envListEl) return "";

  const textArea = envListEl.querySelector("textarea");
  return textArea ? textArea.value : "";
}

window.addEventListener("DOMContentLoaded", async () => {
  statusEl = document.querySelector("#server-status");
  statusTextEl = document.querySelector("#status-text");
  startBtn = document.querySelector("#start-btn");
  stopBtn = document.querySelector("#stop-btn");
  restartBtn = document.querySelector("#restart-btn");
  tabHeaders = document.querySelectorAll(".tab-header");
  portInput = document.querySelector("#port-input");
  logsEl = document.querySelector("#logs");
  workingDirInput = document.querySelector("#working-dir-input");
  browseBtn = document.querySelector("#browse-btn");
  saveConfigBtn = document.querySelector("#save-config-btn");
  clearLogsBtn = document.querySelector("#clear-logs");

  envPanel = document.querySelector("#env-panel");
  envListEl = document.querySelector("#env-list");

  saveEnvBtn = document.querySelector("#save-env-btn");
  loadEnvBtn = document.querySelector("#load-env-btn");
  envFilePathEl = document.querySelector("#env-file-path");

  startBtn?.addEventListener("click", startServer);
  stopBtn?.addEventListener("click", stopServer);
  restartBtn?.addEventListener("click", restartServer);
  // Tab switching
  tabHeaders?.forEach(header => {
    header.addEventListener("click", (e) => {
      const tabName = (e.target as HTMLElement).dataset.tab;
      if (tabName) {
        switchTab(tabName);
      }
    });
  });
  browseBtn?.addEventListener("click", browseWorkingDirectory);
  saveConfigBtn?.addEventListener("click", saveConfig);
  clearLogsBtn?.addEventListener("click", clearLogs);

  saveEnvBtn?.addEventListener("click", saveEnvFileRaw);
  loadEnvBtn?.addEventListener("click", loadEnvFileRaw);

  // Listen for server output events
  await listen("server-output", (event) => {
    const output = event.payload as ServerOutput;
    addServerOutput(output);
  });

  // Update status every 2 seconds
  setInterval(updateServerStatus, 2000);

  // Initial loads
  loadServerConfig();
  updateServerStatus();
  getEnvFilePath();
  loadEnvFileRaw();
});

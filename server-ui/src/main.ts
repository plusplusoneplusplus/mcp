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
let startupTimeoutId: number | null = null; // Track startup timeout
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
let forceKillBtn: HTMLElement | null;
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

    // Clear startup timeout since server is now ready
    if (startupTimeoutId) {
      clearTimeout(startupTimeoutId);
      startupTimeoutId = null;
    }

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

    // Clear any existing startup timeout
    if (startupTimeoutId) {
      clearTimeout(startupTimeoutId);
    }

    // Set a timeout to reset state if server doesn't become ready
    startupTimeoutId = window.setTimeout(() => {
      if (serverStatus.running && !serverReady) {
        addLog("Server startup timeout - resetting state. Check if port is available.");
        serverReady = false;
        updateServerStatus(); // This will refresh the actual server status
      }
    }, 30000); // 30 second timeout

    serverStatus = await invoke("start_server", { port });
    updateUI();
    addLog(`Server started successfully (PID: ${serverStatus.pid})`);
  } catch (error) {
    console.error("Failed to start server:", error);
    addLog(`Failed to start server: ${error}`);

    // Clear timeout on startup failure
    if (startupTimeoutId) {
      clearTimeout(startupTimeoutId);
      startupTimeoutId = null;
    }

    // Reset state on startup failure
    serverReady = false;
    await updateServerStatus();
  }
}

async function stopServer() {
  try {
    addLog("Stopping server...");
    serverStatus = await invoke("stop_server");

    // Reset server ready state when stopping
    serverReady = false;

    // Clear any startup timeout
    if (startupTimeoutId) {
      clearTimeout(startupTimeoutId);
      startupTimeoutId = null;
    }

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

    // Clear any existing startup timeout
    if (startupTimeoutId) {
      clearTimeout(startupTimeoutId);
    }

    // Set a timeout to reset state if server doesn't become ready
    startupTimeoutId = window.setTimeout(() => {
      if (serverStatus.running && !serverReady) {
        addLog("Server restart timeout - resetting state. Check if port is available.");
        serverReady = false;
        updateServerStatus(); // This will refresh the actual server status
      }
    }, 30000); // 30 second timeout

    serverStatus = await invoke("restart_server", { port });
    updateUI();
    addLog(`Server restarted successfully (PID: ${serverStatus.pid})`);
  } catch (error) {
    console.error("Failed to restart server:", error);
    addLog(`Failed to restart server: ${error}`);

    // Clear timeout on restart failure
    if (startupTimeoutId) {
      clearTimeout(startupTimeoutId);
      startupTimeoutId = null;
    }

    // Reset state on restart failure
    serverReady = false;
    await updateServerStatus();
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

function showErrorNotification(message: string) {
  // Create a temporary error notification element
  const notification = document.createElement("div");
  notification.className = "error-notification";
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background-color: #f44336;
    color: white;
    padding: 16px;
    border-radius: 4px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    max-width: 400px;
    word-wrap: break-word;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 14px;
    line-height: 1.4;
  `;

  document.body.appendChild(notification);

  // Remove the notification after 5 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 5000);
}

function showSuccessNotification(message: string) {
  // Create a temporary success notification element
  const notification = document.createElement("div");
  notification.className = "success-notification";
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background-color: #4caf50;
    color: white;
    padding: 16px;
    border-radius: 4px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    max-width: 400px;
    word-wrap: break-word;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 14px;
    line-height: 1.4;
  `;

  document.body.appendChild(notification);

  // Remove the notification after 3 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 3000);
}

async function forceKillPort() {
  if (!portInput) return;

  const port = parseInt(portInput.value);
  if (isNaN(port) || port < 1000 || port > 65535) {
    showErrorNotification("Please enter a valid port number in the Config tab (1000-65535)");
    return;
  }

  try {
    addLog(`Checking for processes using port ${port}...`);

    // First, find what processes are using the port
    const processes: string[] = await invoke("find_port_processes", { port });

    if (processes.length === 0) {
      showSuccessNotification(`No processes found using port ${port}`);
      addLog(`No processes found using port ${port}`);
      return;
    }

    // Show confirmation dialog
    const processList = processes.join('\n');
    const confirmed = confirm(
      `Found ${processes.length} process(es) using port ${port}:\n\n${processList}\n\nDo you want to kill these processes?`
    );

    if (!confirmed) {
      addLog("Force kill cancelled by user");
      return;
    }

    addLog(`Killing processes using port ${port}...`);

    // Kill the processes
    const result: string = await invoke("kill_port_processes", { port });
    showSuccessNotification(result);
    addLog(`Force kill completed: ${result}`);

    // Reset server state after force kill
    serverReady = false;

    // Clear any startup timeout
    if (startupTimeoutId) {
      clearTimeout(startupTimeoutId);
      startupTimeoutId = null;
    }

    // Explicitly set server status to stopped after force kill
    serverStatus = { running: false };
    updateUI();

    // Also update from backend to ensure consistency
    await updateServerStatus();
    addLog("Server state reset - you can now start the server");

  } catch (error) {
    const errorMessage = `Failed to kill processes on port ${port}: ${error}`;
    showErrorNotification(errorMessage);
    addLog(errorMessage);
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
  forceKillBtn = document.querySelector("#force-kill-btn");

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
  forceKillBtn?.addEventListener("click", forceKillPort);

  saveEnvBtn?.addEventListener("click", saveEnvFileRaw);
  loadEnvBtn?.addEventListener("click", loadEnvFileRaw);

  // Listen for server output events
  await listen("server-output", (event) => {
    const output = event.payload as ServerOutput;
    addServerOutput(output);
  });

  // Listen for server startup failure events
  await listen("server-startup-failed", (event) => {
    const output = event.payload as ServerOutput;
    addServerOutput(output);

    // Force update server status to reflect the failure
    setTimeout(updateServerStatus, 500);

    // Show error notification
    showErrorNotification("Server startup failed: Port already in use. Please try a different port or stop any existing server.");
  });

  // Update status every 2 seconds
  setInterval(updateServerStatus, 2000);

  // Initial loads
  loadServerConfig();
  updateServerStatus();
  getEnvFilePath();
  loadEnvFileRaw();
});

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

let serverStatus: ServerStatus = { running: false };
let serverConfig: ServerConfig = { default_port: 8000 };
let statusEl: HTMLElement | null;
let statusTextEl: HTMLElement | null;
let startBtn: HTMLElement | null;
let stopBtn: HTMLElement | null;
let restartBtn: HTMLElement | null;
let configToggleBtn: HTMLElement | null;
let configPanel: HTMLElement | null;
let portInput: HTMLInputElement | null;
let logsEl: HTMLElement | null;
let workingDirInput: HTMLInputElement | null;
let browseBtn: HTMLElement | null;
let saveConfigBtn: HTMLElement | null;
let clearLogsBtn: HTMLElement | null;

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
    statusEl.className = serverStatus.running ? "status running" : "status stopped";
  }

  if (statusTextEl) {
    statusTextEl.textContent = serverStatus.running
      ? `Running (PID: ${serverStatus.pid}, Port: ${serverStatus.port})`
      : "Stopped";
  }

  if (startBtn) startBtn.style.display = serverStatus.running ? "none" : "inline-flex";
  if (stopBtn) stopBtn.style.display = serverStatus.running ? "inline-flex" : "none";
  if (restartBtn) restartBtn.style.display = serverStatus.running ? "inline-flex" : "none";
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
}

async function startServer() {
  try {
    const port = portInput?.value ? parseInt(portInput.value) : serverConfig.default_port;
    addLog(`Starting server on port ${port}...`);

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

function toggleConfig() {
  if (configPanel) {
    configPanel.classList.toggle("collapsed");
  }
}

function clearLogs() {
  if (logsEl) {
    logsEl.innerHTML = "";
    addLog("Logs cleared");
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  statusEl = document.querySelector("#server-status");
  statusTextEl = document.querySelector("#status-text");
  startBtn = document.querySelector("#start-btn");
  stopBtn = document.querySelector("#stop-btn");
  restartBtn = document.querySelector("#restart-btn");
  configToggleBtn = document.querySelector("#config-toggle");
  configPanel = document.querySelector("#config-panel");
  portInput = document.querySelector("#port-input");
  logsEl = document.querySelector("#logs");
  workingDirInput = document.querySelector("#working-dir-input");
  browseBtn = document.querySelector("#browse-btn");
  saveConfigBtn = document.querySelector("#save-config-btn");
  clearLogsBtn = document.querySelector("#clear-logs");

  startBtn?.addEventListener("click", startServer);
  stopBtn?.addEventListener("click", stopServer);
  restartBtn?.addEventListener("click", restartServer);
  configToggleBtn?.addEventListener("click", toggleConfig);
  browseBtn?.addEventListener("click", browseWorkingDirectory);
  saveConfigBtn?.addEventListener("click", saveConfig);
  clearLogsBtn?.addEventListener("click", clearLogs);

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
});

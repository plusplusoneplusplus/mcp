use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::path::PathBuf;
use std::io::{BufRead, BufReader};
use std::fs;
use tauri::{State, Emitter};
use serde::{Deserialize, Serialize};

#[cfg(unix)]
use std::os::unix::process::CommandExt;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ServerStatus {
    pub running: bool,
    pub pid: Option<u32>,
    pub port: Option<u16>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ServerConfig {
    pub working_directory: Option<String>,
    pub default_port: u16,
}

#[derive(Debug, Serialize, Clone)]
pub struct ServerOutput {
    pub timestamp: String,
    pub stream: String, // "stdout" or "stderr"
    pub content: String,
}

pub struct ServerManager {
    process: Arc<Mutex<Option<Child>>>,
    status: Arc<Mutex<ServerStatus>>,
    config: Arc<Mutex<ServerConfig>>,
}

fn get_config_path() -> Result<PathBuf, String> {
    let config_dir = dirs::config_dir()
        .ok_or("Failed to get config directory")?
        .join("mcp-server-manager");

    fs::create_dir_all(&config_dir)
        .map_err(|e| format!("Failed to create config directory: {}", e))?;

    Ok(config_dir.join("config.json"))
}

fn load_config_from_file() -> ServerConfig {
    match get_config_path() {
        Ok(config_path) => {
            if config_path.exists() {
                match fs::read_to_string(&config_path) {
                    Ok(content) => {
                        match serde_json::from_str::<ServerConfig>(&content) {
                            Ok(config) => return config,
                            Err(e) => eprintln!("Failed to parse config file: {}", e),
                        }
                    }
                    Err(e) => eprintln!("Failed to read config file: {}", e),
                }
            }
        }
        Err(e) => eprintln!("Failed to get config path: {}", e),
    }

    // Return default config if loading fails
    ServerConfig {
        working_directory: None,
        default_port: 8000,
    }
}

fn save_config_to_file(config: &ServerConfig) -> Result<(), String> {
    let config_path = get_config_path()?;
    let content = serde_json::to_string_pretty(config)
        .map_err(|e| format!("Failed to serialize config: {}", e))?;

    fs::write(&config_path, content)
        .map_err(|e| format!("Failed to write config file: {}", e))?;

    Ok(())
}

impl ServerManager {
    pub fn new() -> Self {
        let loaded_config = load_config_from_file();

        Self {
            process: Arc::new(Mutex::new(None)),
            status: Arc::new(Mutex::new(ServerStatus {
                running: false,
                pid: None,
                port: None,
            })),
            config: Arc::new(Mutex::new(loaded_config)),
        }
    }
}

async fn start_server_internal(manager: &ServerManager, app: tauri::AppHandle, port: Option<u16>) -> Result<ServerStatus, String> {
    let mut process_guard = manager.process.lock().map_err(|_| "Failed to lock process")?;
    let mut status_guard = manager.status.lock().map_err(|_| "Failed to lock status")?;
    let config_guard = manager.config.lock().map_err(|_| "Failed to lock config")?;

    if status_guard.running {
        return Ok(status_guard.clone());
    }

    let port = port.unwrap_or(config_guard.default_port);

    // Determine the working directory
    let working_dir = if let Some(custom_dir) = &config_guard.working_directory {
        PathBuf::from(custom_dir)
    } else {
        // Default behavior: parent directory of current working directory
        std::env::current_dir()
            .map_err(|_| "Failed to get current directory")?
            .parent()
            .ok_or("Failed to get parent directory")?
            .to_path_buf()
    };

    // Drop the config guard to avoid holding multiple locks
    drop(config_guard);

    // Check if server/main.py exists in the working directory
    let server_main_path = working_dir.join("server").join("main.py");
    if !server_main_path.exists() {
        return Err(format!(
            "server/main.py not found in working directory: {}. Expected path: {}",
            working_dir.display(),
            server_main_path.display()
        ));
    }

    let mut command = Command::new("uv");
    command
        .args(&["run", "server/main.py", "--port", &port.to_string()])
        .current_dir(&working_dir)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    // Create a new process group on Unix to enable killing entire process tree
    #[cfg(unix)]
    command.process_group(0);

    let mut child = command
        .spawn()
        .map_err(|e| format!("Failed to start server in {}: {}", working_dir.display(), e))?;

    let pid = child.id();

    // Capture stdout and stderr
    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
    let stderr = child.stderr.take().ok_or("Failed to capture stderr")?;

    // Spawn tasks to read output streams
    let app_clone = app.clone();
    tokio::spawn(async move {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(line) = line {
                let output = ServerOutput {
                    timestamp: chrono::Utc::now().format("%H:%M:%S").to_string(),
                    stream: "stdout".to_string(),
                    content: line,
                };
                let _ = app_clone.emit("server-output", &output);
            }
        }
    });

    let app_clone = app.clone();
    tokio::spawn(async move {
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            if let Ok(line) = line {
                let output = ServerOutput {
                    timestamp: chrono::Utc::now().format("%H:%M:%S").to_string(),
                    stream: "stderr".to_string(),
                    content: line,
                };
                let _ = app_clone.emit("server-output", &output);
            }
        }
    });

    *process_guard = Some(child);

    status_guard.running = true;
    status_guard.pid = Some(pid);
    status_guard.port = Some(port);

    Ok(status_guard.clone())
}

#[tauri::command]
async fn start_server(manager: State<'_, ServerManager>, app: tauri::AppHandle, port: Option<u16>) -> Result<ServerStatus, String> {
    start_server_internal(&*manager, app, port).await
}

async fn stop_server_internal(manager: &ServerManager) -> Result<ServerStatus, String> {
    let mut process_guard = manager.process.lock().map_err(|_| "Failed to lock process")?;
    let mut status_guard = manager.status.lock().map_err(|_| "Failed to lock status")?;

    if let Some(mut child) = process_guard.take() {
        let pid = child.id();

        // Try graceful termination first
        if child.kill().is_err() {
            // If graceful kill fails, try force kill
            #[cfg(unix)]
            {
                // Kill the entire process group to ensure all child processes are terminated
                unsafe {
                    // Kill process group (negative PID kills the process group)
                    libc::kill(-(pid as i32), libc::SIGKILL);
                    // Also kill the specific process as fallback
                    libc::kill(pid as i32, libc::SIGKILL);
                }
            }

            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                use std::process::Command;
                // Use taskkill with /T flag to kill process tree
                let _ = Command::new("taskkill")
                    .args(&["/F", "/T", "/PID", &pid.to_string()])
                    .creation_flags(0x08000000) // CREATE_NO_WINDOW
                    .output();
            }
        } else {
            // Even if graceful kill succeeded, also kill process group on Unix to be sure
            #[cfg(unix)]
            {
                unsafe {
                    libc::kill(-(pid as i32), libc::SIGTERM);
                }
            }
        }
        let _ = child.wait();
    }

    status_guard.running = false;
    status_guard.pid = None;
    status_guard.port = None;

    Ok(status_guard.clone())
}

#[tauri::command]
async fn stop_server(manager: State<'_, ServerManager>) -> Result<ServerStatus, String> {
    stop_server_internal(&*manager).await
}

#[tauri::command]
async fn restart_server(manager: State<'_, ServerManager>, app: tauri::AppHandle, port: Option<u16>) -> Result<ServerStatus, String> {
    stop_server_internal(&*manager).await?;
    tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
    start_server_internal(&*manager, app, port).await
}

#[tauri::command]
async fn get_server_status(manager: State<'_, ServerManager>) -> Result<ServerStatus, String> {
    let status_guard = manager.status.lock().map_err(|_| "Failed to lock status")?;
    Ok(status_guard.clone())
}

#[tauri::command]
async fn get_server_config(manager: State<'_, ServerManager>) -> Result<ServerConfig, String> {
    let config_guard = manager.config.lock().map_err(|_| "Failed to lock config")?;
    Ok(config_guard.clone())
}

#[tauri::command]
async fn set_server_config(manager: State<'_, ServerManager>, config: ServerConfig) -> Result<ServerConfig, String> {
    // Save to file first
    save_config_to_file(&config)?;

    // Then update in-memory config
    let mut config_guard = manager.config.lock().map_err(|_| "Failed to lock config")?;
    *config_guard = config.clone();

    Ok(config)
}

#[tauri::command]
async fn browse_working_directory(_app: tauri::AppHandle) -> Result<Option<String>, String> {
    // Return the current parent directory as a suggestion
    let suggested_path = std::env::current_dir()
        .ok()
        .and_then(|p| p.parent().map(|parent| parent.to_string_lossy().to_string()));

    Ok(suggested_path)
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(ServerManager::new())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            start_server,
            stop_server,
            restart_server,
            get_server_status,
            get_server_config,
            set_server_config,
            browse_working_directory
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

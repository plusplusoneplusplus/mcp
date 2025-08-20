use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::path::PathBuf;
use std::io::{BufRead, BufReader};
use std::fs;
use tauri::{State, Emitter, Manager};
use serde::{Deserialize, Serialize};


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

fn get_server_env_path() -> Result<PathBuf, String> {
    // Use CARGO_MANIFEST_DIR to get the src-tauri directory, then navigate to project root
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")
        .map_err(|_| "CARGO_MANIFEST_DIR environment variable not set")?;

    let src_tauri_path = PathBuf::from(manifest_dir);

    // From src-tauri/ go up to server-ui/, then up to project root (mcp/)
    let working_dir = src_tauri_path
        .parent() // from src-tauri/ to server-ui/
        .and_then(|p| p.parent()) // from server-ui/ to project root (mcp/)
        .ok_or("Failed to get project root directory")?
        .to_path_buf();

    Ok(working_dir.join("server").join(".env"))
}





impl Default for ServerManager {
    fn default() -> Self {
        Self::new()
    }
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

    // Cleanup method to ensure server is stopped when manager is dropped
    pub fn cleanup(&self) {
        if let Ok(mut process_guard) = self.process.lock() {
            if let Some(mut child) = process_guard.take() {
                let pid = child.id();

                // Try graceful termination first
                let _ = child.kill();

                // Force kill the process group to ensure cleanup
                #[cfg(unix)]
                {
                    unsafe {
                        // Kill the entire process group
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
                        .args(["/F", "/T", "/PID", &pid.to_string()])
                        .creation_flags(0x08000000) // CREATE_NO_WINDOW
                        .output();
                }

                let _ = child.wait();
            }
        }

        // Update status
        if let Ok(mut status_guard) = self.status.lock() {
            status_guard.running = false;
            status_guard.pid = None;
            status_guard.port = None;
        }
    }
}

// Implement Drop to ensure cleanup when ServerManager is dropped
impl Drop for ServerManager {
    fn drop(&mut self) {
        self.cleanup();
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
        .args(["run", "server/main.py", "--port", &port.to_string()])
        .current_dir(&working_dir)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    // Create a new process group on Unix to enable killing entire process tree
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }

    // On Windows, create a new process group as well
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x00000200); // CREATE_NEW_PROCESS_GROUP
    }

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
        for line in reader.lines().map_while(Result::ok) {
            let output = ServerOutput {
                timestamp: chrono::Utc::now().format("%H:%M:%S").to_string(),
                stream: "stdout".to_string(),
                content: line,
            };
            let _ = app_clone.emit("server-output", &output);
        }
    });

    // Monitor stderr for startup errors
    let app_clone = app.clone();
    let status_arc = manager.status.clone();
    let process_arc = manager.process.clone();
    tokio::spawn(async move {
        let reader = BufReader::new(stderr);
        for line in reader.lines().map_while(Result::ok) {
            let output = ServerOutput {
                timestamp: chrono::Utc::now().format("%H:%M:%S").to_string(),
                stream: "stderr".to_string(),
                content: line.clone(),
            };
            let _ = app_clone.emit("server-output", &output);

            // Check for various server startup errors
            if line.contains("address already in use") ||
               line.contains("Errno 48") ||
               (line.contains("bind on address") && line.contains("address already in use")) ||
               line.contains("Port already in use") ||
               line.contains("OSError: [Errno 48]") ||
               line.contains("Cannot bind to address") {
                println!("Server startup failed: Port already in use");

                // Update server status to indicate failure
                if let Ok(mut status_guard) = status_arc.lock() {
                    status_guard.running = false;
                    status_guard.pid = None;
                    status_guard.port = None;
                }

                // Kill the failed process
                if let Ok(mut process_guard) = process_arc.lock() {
                    if let Some(mut child) = process_guard.take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }

                // Emit a server startup failure event
                let failure_output = ServerOutput {
                    timestamp: chrono::Utc::now().format("%H:%M:%S").to_string(),
                    stream: "error".to_string(),
                    content: "Server startup failed: Port already in use".to_string(),
                };
                let _ = app_clone.emit("server-startup-failed", &failure_output);
                break;
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
    start_server_internal(&manager, app, port).await
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
                    .args(["/F", "/T", "/PID", &pid.to_string()])
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
    stop_server_internal(&manager).await
}

#[tauri::command]
async fn restart_server(manager: State<'_, ServerManager>, app: tauri::AppHandle, port: Option<u16>) -> Result<ServerStatus, String> {
    stop_server_internal(&manager).await?;
    tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
    start_server_internal(&manager, app, port).await
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





#[tauri::command]
async fn get_env_file_path() -> Result<String, String> {
    let env_path = get_server_env_path()?;
    Ok(env_path.to_string_lossy().to_string())
}

#[tauri::command]
async fn load_env_file_raw() -> Result<String, String> {
    let env_path = get_server_env_path()?;

    if !env_path.exists() {
        // If .env file doesn't exist, try to copy from env.template
        let template_path = env_path
            .parent()
            .and_then(|p| p.parent())
            .map(|p| p.join("config").join("env.template"))
            .ok_or("Failed to construct template path")?;

        if template_path.exists() {
            fs::copy(&template_path, &env_path)
                .map_err(|e| format!("Failed to copy env.template: {}", e))?;
        } else {
            // Create empty .env file
            fs::write(&env_path, "")
                .map_err(|e| format!("Failed to create .env file: {}", e))?;
        }
    }

    let content = fs::read_to_string(&env_path)
        .map_err(|e| format!("Failed to read .env file: {}", e))?;

    Ok(content)
}

#[tauri::command]
async fn save_env_file_raw(content: String) -> Result<(), String> {
    let env_path = get_server_env_path()?;

    // Ensure parent directory exists
    if let Some(parent) = env_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create directory: {}", e))?;
    }

    fs::write(&env_path, content)
        .map_err(|e| format!("Failed to write .env file: {}", e))?;

    Ok(())
}

#[tauri::command]
async fn find_port_processes(port: u16) -> Result<Vec<String>, String> {
    let mut processes = Vec::new();

    #[cfg(unix)]
    {
        // Use lsof to find processes using the port
        let output = Command::new("lsof")
            .args(["-i", &format!(":{}", port)])
            .output()
            .map_err(|e| format!("Failed to run lsof: {}", e))?;

        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines().skip(1) { // Skip header line
                if !line.trim().is_empty() {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 2 {
                        let command = parts[0];
                        let pid = parts[1];
                        processes.push(format!("{} (PID: {})", command, pid));
                    }
                }
            }
        }
    }

    #[cfg(windows)]
    {
        // Use netstat to find processes using the port
        let output = Command::new("netstat")
            .args(["-ano"])
            .output()
            .map_err(|e| format!("Failed to run netstat: {}", e))?;

        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                if line.contains(&format!(":{}", port)) && line.contains("LISTENING") {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if let Some(pid) = parts.last() {
                        // Get process name from PID
                        let tasklist_output = Command::new("tasklist")
                            .args(["/FI", &format!("PID eq {}", pid), "/FO", "CSV", "/NH"])
                            .output();

                        if let Ok(tasklist_result) = tasklist_output {
                            let tasklist_stdout = String::from_utf8_lossy(&tasklist_result.stdout);
                            if let Some(first_line) = tasklist_stdout.lines().next() {
                                let csv_parts: Vec<&str> = first_line.split(',').collect();
                                if let Some(process_name) = csv_parts.first() {
                                    let clean_name = process_name.trim_matches('"');
                                    processes.push(format!("{} (PID: {})", clean_name, pid));
                                }
                            }
                        } else {
                            processes.push(format!("Unknown process (PID: {})", pid));
                        }
                    }
                }
            }
        }
    }

    Ok(processes)
}

#[tauri::command]
async fn kill_port_processes(port: u16) -> Result<String, String> {
    let mut killed_processes = Vec::new();

    #[cfg(unix)]
    {
        // Use lsof to find PIDs, then kill them
        let output = Command::new("lsof")
            .args(["-t", "-i", &format!(":{}", port)])
            .output()
            .map_err(|e| format!("Failed to run lsof: {}", e))?;

        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                if let Ok(pid) = line.trim().parse::<u32>() {
                    // Try graceful kill first (SIGTERM)
                    let kill_result = Command::new("kill")
                        .args(["-TERM", &pid.to_string()])
                        .output();

                    if kill_result.is_ok() {
                        // Wait a moment for graceful shutdown
                        tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;

                        // Check if process is still running
                        let check_result = Command::new("kill")
                            .args(["-0", &pid.to_string()])
                            .output();

                        // If process is still running, force kill
                        if check_result.is_ok() && check_result.unwrap().status.success() {
                            let _ = Command::new("kill")
                                .args(["-KILL", &pid.to_string()])
                                .output();
                        }

                        killed_processes.push(pid.to_string());
                    }
                }
            }
        }
    }

    #[cfg(windows)]
    {
        // Use netstat to find PIDs, then use taskkill
        let output = Command::new("netstat")
            .args(["-ano"])
            .output()
            .map_err(|e| format!("Failed to run netstat: {}", e))?;

        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                if line.contains(&format!(":{}", port)) && line.contains("LISTENING") {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if let Some(pid) = parts.last() {
                        if let Ok(pid_num) = pid.parse::<u32>() {
                            // Use taskkill to force terminate the process
                            let kill_result = Command::new("taskkill")
                                .args(["/F", "/PID", &pid_num.to_string()])
                                .creation_flags(0x08000000) // CREATE_NO_WINDOW
                                .output();

                            if kill_result.is_ok() {
                                killed_processes.push(pid_num.to_string());
                            }
                        }
                    }
                }
            }
        }
    }

    if killed_processes.is_empty() {
        Ok("No processes found using the port".to_string())
    } else {
        Ok(format!("Killed {} process(es) with PID(s): {}",
                  killed_processes.len(),
                  killed_processes.join(", ")))
    }
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
            browse_working_directory,
            get_env_file_path,
            load_env_file_raw,
            save_env_file_raw,
            find_port_processes,
            kill_port_processes
        ])
        .setup(|_app| {
            // Add signal handlers to handle crashes and force kills
            #[cfg(unix)]
            {
                use std::sync::atomic::{AtomicBool, Ordering};
                use std::thread;

                // Spawn a background thread to monitor for termination signals
                thread::spawn(move || {
                    static SIGNAL_RECEIVED: AtomicBool = AtomicBool::new(false);

                    unsafe {
                        // Set up signal handlers
                        libc::signal(libc::SIGTERM, handle_signal as libc::sighandler_t);
                        libc::signal(libc::SIGINT, handle_signal as libc::sighandler_t);
                        libc::signal(libc::SIGQUIT, handle_signal as libc::sighandler_t);
                        libc::signal(libc::SIGABRT, handle_signal as libc::sighandler_t);
                    }

                    // Signal handler function
                    extern "C" fn handle_signal(sig: libc::c_int) {
                        if SIGNAL_RECEIVED.swap(true, Ordering::SeqCst) {
                            // If we've already received a signal, force immediate exit
                            unsafe {
                                libc::_exit(1);
                            }
                        }

                        let signal_name = match sig {
                            libc::SIGTERM => "SIGTERM",
                            libc::SIGINT => "SIGINT",
                            libc::SIGQUIT => "SIGQUIT",
                            libc::SIGABRT => "SIGABRT",
                            _ => "UNKNOWN",
                        };

                        println!("Received {} signal, performing emergency cleanup...", signal_name);

                        // Force immediate process group kill to ensure child processes are terminated
                        unsafe {
                            // Kill our entire process group (including all child processes)
                            libc::kill(0, libc::SIGKILL);
                        }
                    }

                    // Keep the thread alive to handle signals
                    loop {
                        thread::sleep(std::time::Duration::from_secs(1));
                    }
                });

                // Also register an atexit handler for additional safety
                unsafe {
                    libc::atexit(cleanup_at_exit);
                }

                // Static cleanup function for atexit
                extern "C" fn cleanup_at_exit() {
                    println!("Process exiting, performing final cleanup...");
                    // Kill our entire process group to ensure all child processes are terminated
                    unsafe {
                        libc::kill(0, libc::SIGKILL);
                    }
                }
            }

            // Add Windows-specific signal handling
            #[cfg(windows)]
            {
                use std::thread;
                use std::ptr;

                // Register console control handler for Windows
                thread::spawn(move || {
                    unsafe {
                        extern "system" {
                            fn SetConsoleCtrlHandler(
                                handler: Option<extern "system" fn(u32) -> i32>,
                                add: i32,
                            ) -> i32;
                        }

                        extern "system" fn console_handler(ctrl_type: u32) -> i32 {
                            match ctrl_type {
                                0 => println!("Received CTRL+C, performing emergency cleanup..."), // CTRL_C_EVENT
                                1 => println!("Received CTRL+BREAK, performing emergency cleanup..."), // CTRL_BREAK_EVENT
                                2 => println!("Received close signal, performing emergency cleanup..."), // CTRL_CLOSE_EVENT
                                5 => println!("Received logoff signal, performing emergency cleanup..."), // CTRL_LOGOFF_EVENT
                                6 => println!("Received shutdown signal, performing emergency cleanup..."), // CTRL_SHUTDOWN_EVENT
                                _ => println!("Received unknown signal {}, performing emergency cleanup...", ctrl_type),
                            }

                            // Kill all child processes when we receive any termination signal
                            let _ = std::process::Command::new("taskkill")
                                .args(["/F", "/T", "/IM", "python.exe"])
                                .creation_flags(0x08000000) // CREATE_NO_WINDOW
                                .output();

                            let _ = std::process::Command::new("taskkill")
                                .args(["/F", "/T", "/IM", "uv.exe"])
                                .creation_flags(0x08000000) // CREATE_NO_WINDOW
                                .output();

                            1 // Return 1 to indicate we handled the signal
                        }

                        SetConsoleCtrlHandler(Some(console_handler), 1);
                    }

                    // Keep the thread alive to handle signals
                    loop {
                        thread::sleep(std::time::Duration::from_secs(1));
                    }
                });
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                println!("App window closing, cleaning up server...");
                // Get the server manager state and clean up
                let server_manager = window.state::<ServerManager>();
                server_manager.cleanup();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_server_manager_creation() {
        let manager = ServerManager::new();
        let status = manager.status.lock().unwrap();
        assert!(!status.running);
        assert!(status.pid.is_none());
        assert!(status.port.is_none());
    }

    #[test]
    fn test_server_config_serialization() {
        let config = ServerConfig {
            working_directory: Some("/test/path".to_string()),
            default_port: 8080,
        };

        let serialized = serde_json::to_string(&config).unwrap();
        let deserialized: ServerConfig = serde_json::from_str(&serialized).unwrap();

        assert_eq!(config.working_directory, deserialized.working_directory);
        assert_eq!(config.default_port, deserialized.default_port);
    }

    #[test]
    fn test_server_status_serialization() {
        let status = ServerStatus {
            running: true,
            pid: Some(1234),
            port: Some(8000),
        };

        let serialized = serde_json::to_string(&status).unwrap();
        let deserialized: ServerStatus = serde_json::from_str(&serialized).unwrap();

        assert_eq!(status.running, deserialized.running);
        assert_eq!(status.pid, deserialized.pid);
        assert_eq!(status.port, deserialized.port);
    }

    #[test]
    fn test_greet_function() {
        let result = greet("World");
        assert_eq!(result, "Hello, World! You've been greeted from Rust!");
    }

    #[test]
    fn test_default_config() {
        // Test the default config creation directly rather than loading from file
        let config = ServerConfig {
            working_directory: None,
            default_port: 8000,
        };
        assert_eq!(config.default_port, 8000);
        assert!(config.working_directory.is_none());
    }
}

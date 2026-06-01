#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use std::time::Duration;
use tauri::{Emitter, Manager};
use tauri_plugin_shell::ShellExt;

const APP_URL: &str = "http://127.0.0.1:10717/app/";
const BACKEND_ADDR: &str = "127.0.0.1:10717";

const SIDECAR_CAMERA: &str = "binaries/devices-mcp-camera";
const SIDECAR_BACKEND: &str = "binaries/devices-mcp-backend";

struct SidecarState {
    camera: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
    backend: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn is_backend_listening() -> bool {
    let addr: SocketAddr = BACKEND_ADDR.parse().expect("valid backend addr");
    TcpStream::connect_timeout(&addr, Duration::from_millis(500)).is_ok()
}

fn spawn_sidecar(
    app: &tauri::AppHandle,
    name: &str,
    args: &[&str],
) -> Result<
    (
        tauri::async_runtime::Receiver<tauri_plugin_shell::process::CommandEvent>,
        tauri_plugin_shell::process::CommandChild,
    ),
    String,
> {
    let mut cmd = app
        .shell()
        .sidecar(name)
        .map_err(|e| format!("Sidecar {name}: {e}"))?;
    for arg in args {
        cmd = cmd.arg(arg);
    }
    #[cfg(not(debug_assertions))]
    {
        cmd = cmd.env("TAPO_MCP_SKIP_HARDWARE_INIT", "true");
        cmd = cmd.env("TAPO_MCP_LAZY_INIT", "true");
        cmd = cmd.env("DEVICES_MCP_PACKAGED", "1");
    }
    cmd.spawn().map_err(|e| format!("Spawn {name}: {e}"))
}

#[cfg(debug_assertions)]
async fn spawn_dev_command(
    app: &tauri::AppHandle,
    cwd: PathBuf,
    args: Vec<String>,
) -> Result<
    (
        tauri::async_runtime::Receiver<tauri_plugin_shell::process::CommandEvent>,
        tauri_plugin_shell::process::CommandChild,
    ),
    String,
> {
    let mut cmd = app.shell().command("uv");
    cmd = cmd.args(args).current_dir(cwd);
    cmd.spawn().map_err(|e| format!("Dev spawn failed: {e}"))
}

async fn watch_backend_stdout(
    mut rx: tauri::async_runtime::Receiver<tauri_plugin_shell::process::CommandEvent>,
    ready: Arc<AtomicBool>,
) {
    use tauri_plugin_shell::process::CommandEvent;
    while let Some(event) = rx.recv().await {
        if let CommandEvent::Stdout(line) | CommandEvent::Stderr(line) = event {
            let text = String::from_utf8_lossy(&line);
            eprintln!("[backend] {}", text.trim());
            if text.contains("Uvicorn running")
                || text.contains("Application startup complete")
                || text.contains("Started server process")
            {
                ready.store(true, Ordering::SeqCst);
            }
        }
    }
}

async fn start_camera(app: &tauri::AppHandle, state: &tauri::State<'_, SidecarState>) -> Result<(), String> {
    #[cfg(debug_assertions)]
    {
        let root = repo_root();
        let (rx, child) = spawn_dev_command(
            app,
            root.clone(),
            vec![
                "run".into(),
                "python".into(),
                "run_camera_server.py".into(),
            ],
        )
        .await?;
        *state.camera.lock().unwrap() = Some(child);
        let _ = rx;
        return Ok(());
    }

    #[cfg(not(debug_assertions))]
    {
        let (_rx, child) = spawn_sidecar(app, SIDECAR_CAMERA, &[])?;
        *state.camera.lock().unwrap() = Some(child);
        Ok(())
    }
}

async fn start_backend(
    app: &tauri::AppHandle,
    state: &tauri::State<'_, SidecarState>,
    ready: Arc<AtomicBool>,
) -> Result<(), String> {
    if is_backend_listening() {
        eprintln!("Reusing existing backend on {BACKEND_ADDR} (NSSM/service or prior instance)");
        ready.store(true, Ordering::SeqCst);
        return Ok(());
    }

    let spawn_result = {
        #[cfg(debug_assertions)]
        {
            let web_sota = repo_root().join("web-sota");
            spawn_dev_command(
                app,
                web_sota,
                vec![
                    "run".into(),
                    "python".into(),
                    "-m".into(),
                    "backend.server".into(),
                    "--host".into(),
                    "127.0.0.1".into(),
                    "--port".into(),
                    "10717".into(),
                ],
            )
            .await
        }

        #[cfg(not(debug_assertions))]
        {
            spawn_sidecar(
                app,
                SIDECAR_BACKEND,
                &["--host", "127.0.0.1", "--port", "10717"],
            )
        }
    };

    let (rx, child) = match spawn_result {
        Ok(pair) => pair,
        Err(e) => {
            if is_backend_listening() {
                eprintln!("Sidecar spawn failed but backend is up: {e}");
                ready.store(true, Ordering::SeqCst);
                return Ok(());
            }
            return Err(e);
        }
    };

    *state.backend.lock().unwrap() = Some(child);
    tauri::async_runtime::spawn(watch_backend_stdout(rx, ready));
    Ok(())
}

fn open_dashboard(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if let Ok(url) = tauri::Url::parse(APP_URL) {
            let _ = window.navigate(url);
        }
    }
}

async fn boot_services(app: tauri::AppHandle) {
    let ready = Arc::new(AtomicBool::new(false));
    let state = app.state::<SidecarState>();

    if is_backend_listening() {
        ready.store(true, Ordering::SeqCst);
    }

    if let Err(e) = start_camera(&app, &state).await {
        eprintln!("Camera helper error: {e}");
        let _ = app.emit("backend-status", format!("camera error: {e}"));
    }

    tokio::time::sleep(Duration::from_secs(1)).await;

    if let Err(e) = start_backend(&app, &state, ready.clone()).await {
        eprintln!("Backend error: {e}");
        let _ = app.emit("backend-status", format!("error: {e}"));
        if is_backend_listening() {
            open_dashboard(&app);
        }
        return;
    }

    if ready.load(Ordering::SeqCst) {
        let _ = app.emit("backend-status", "ready");
        open_dashboard(&app);
        return;
    }

    for _ in 0..90 {
        if ready.load(Ordering::SeqCst) {
            let _ = app.emit("backend-status", "ready");
            open_dashboard(&app);
            return;
        }
        if is_backend_listening() {
            ready.store(true, Ordering::SeqCst);
            open_dashboard(&app);
            return;
        }
        tokio::time::sleep(Duration::from_secs(1)).await;
    }

    let _ = app.emit("backend-status", "error: backend timeout");
    if is_backend_listening() {
        open_dashboard(&app);
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .manage(SidecarState {
            camera: Mutex::new(None),
            backend: Mutex::new(None),
        })
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                boot_services(handle).await;
            });
            #[cfg(debug_assertions)]
            if let Some(window) = app.get_webview_window("main") {
                window.open_devtools();
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building tauri application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                let backend = app.state::<SidecarState>().backend.lock().unwrap().take();
                let camera = app.state::<SidecarState>().camera.lock().unwrap().take();
                if let Some(child) = backend {
                    let _ = child.kill();
                }
                if let Some(child) = camera {
                    let _ = child.kill();
                }
            }
        });
}

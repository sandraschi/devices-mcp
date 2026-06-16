#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod tray;

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

struct SidecarState {
    camera: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
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
        let _ = (app, state);
        Ok(())
    }
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
    let sidecar_state = app.state::<SidecarState>();
    let backend_state = app.state::<backend::BackendProcess>();

    if is_backend_listening() {
        ready.store(true, Ordering::SeqCst);
    }

    if let Err(e) = start_camera(&app, &sidecar_state).await {
        eprintln!("Camera helper error: {e}");
        let _ = app.emit("backend-status", format!("camera error: {e}"));
    }

    tokio::time::sleep(Duration::from_secs(1)).await;

    // Backend via std::process::Command (embedded bundle.resources)
    if !is_backend_listening() {
        if let Err(e) = backend::spawn_backend(app.clone(), backend_state.inner()) {
            eprintln!("Backend error: {e}");
            let _ = app.emit("backend-status", format!("error: {e}"));
            if is_backend_listening() {
                open_dashboard(&app);
            }
            return;
        }
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
    let poller_running = Arc::new(AtomicBool::new(true));
    let poller_flag = poller_running.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_notification::init())
        .manage(SidecarState {
            camera: Mutex::new(None),
        })
        .manage(backend::BackendProcess(std::sync::Mutex::new(None)))
        .setup(move |app| {
            let handle = app.handle().clone();

            if let Err(e) = tray::setup_tray(&handle) {
                eprintln!("Tray setup error: {e}");
            }

            let boot_handle = handle.clone();
            tauri::async_runtime::spawn(async move {
                boot_services(boot_handle).await;
            });

            tray::start_doorbell_poller(handle.clone(), poller_flag.clone());

            #[cfg(debug_assertions)]
            if let Some(window) = app.get_webview_window("main") {
                window.open_devtools();
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building tauri application")
        .run(move |app, event| {
            if let tauri::RunEvent::Exit = event {
                poller_running.store(false, Ordering::SeqCst);
                let camera = app.state::<SidecarState>().camera.lock().unwrap().take();
                if let Some(child) = camera {
                    let _ = child.kill();
                }
                if let Some(mut child) = app.state::<backend::BackendProcess>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use serde::Deserialize;
use tauri::menu::{MenuBuilder, MenuItemBuilder};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Emitter, Manager};

const POLL_INTERVAL_SECS: u64 = 10;
const BACKEND_URL: &str = "http://127.0.0.1:10717";

#[derive(Debug, Deserialize)]
struct RingEventsResponse {
    events: Option<Vec<RingEvent>>,
}

#[derive(Debug, Deserialize, Clone)]
struct RingEvent {
    event_type: Option<String>,
    device_name: Option<String>,
    timestamp: Option<String>,
}

pub fn setup_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let open = MenuItemBuilder::with_id("open", "Open Dashboard").build(app)?;
    let quit = MenuItemBuilder::with_id("quit", "Quit").build(app)?;

    let menu = MenuBuilder::new(app)
        .item(&open)
        .separator()
        .item(&quit)
        .build()?;

    let _tray = TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .tooltip("Devices MCP")
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open" => {
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.show();
                    let _ = w.set_focus();
                }
            }
            "quit" => {
                app.exit(0);
            }
            _ => {}
        })
        .build(app)?;

    Ok(())
}

pub fn start_doorbell_poller(app: AppHandle, running: Arc<AtomicBool>) {
    tauri::async_runtime::spawn(async move {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .unwrap();

        let mut last_ding_ts: Option<String> = None;

        while running.load(Ordering::SeqCst) {
            tokio::time::sleep(Duration::from_secs(POLL_INTERVAL_SECS)).await;

            let resp = client
                .get(format!("{BACKEND_URL}/api/ring/events?limit=5"))
                .send()
                .await;

            let Ok(resp) = resp else { continue };
            let Ok(data) = resp.json::<RingEventsResponse>().await else {
                continue;
            };

            let events = data.events.unwrap_or_default();
            let latest_ding = events
                .iter()
                .find(|e| e.event_type.as_deref() == Some("ding"));

            if let Some(ding) = latest_ding {
                let ts = ding.timestamp.clone().unwrap_or_default();
                if !ts.is_empty() && last_ding_ts.as_deref() != Some(&ts) {
                    let is_first = last_ding_ts.is_some();
                    last_ding_ts = Some(ts);

                    if is_first {
                        let title = "🔔 Doorbell";
                        let body = ding
                            .device_name
                            .clone()
                            .unwrap_or_else(|| "Someone at the door".into());

                        let _ = app.emit("doorbell-ding", &body);

                        use tauri_plugin_notification::NotificationExt;
                        let _ = app
                            .notification()
                            .builder()
                            .title(title)
                            .body(&body)
                            .show();
                    }
                }
            }
        }
    });
}

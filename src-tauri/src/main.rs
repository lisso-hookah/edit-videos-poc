// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

const API_PORT: u16 = 18374;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let handle = app.handle().clone();

            // Spawn the Python FastAPI sidecar in a background thread so setup doesn't block
            std::thread::spawn(move || {
                match handle
                    .shell()
                    .sidecar("edit-videos-server")
                    .expect("sidecar binary not found — run scripts/build_sidecar.sh first")
                    .args(["--port", &API_PORT.to_string()])
                    .spawn()
                {
                    Ok((_rx, _child)) => {
                        // Keep the child handle alive for the lifetime of this thread.
                        // The thread parks here; when the app exits the handle drops and
                        // the OS cleans up the child process.
                        std::thread::park();
                    }
                    Err(e) => {
                        eprintln!("[edit-videos] Failed to spawn sidecar: {e}");
                    }
                }
            });

            // Give the server time to bind before the window tries to connect
            std::thread::sleep(Duration::from_millis(1500));

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

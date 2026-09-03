#[tauri::command]
fn ping() -> String { "pong".into() }

#[tauri::command]
fn get_subjects() -> Vec<Subject> {
    vec![
        Subject { id: "main".into(), name: "Main".into(), color: "#14b8a6".into() },
        Subject { id: "calc".into(), name: "Calculus II".into(), color: "#f97316".into() },
        Subject { id: "bio".into(), name: "Bio 101".into(), color: "#a855f7".into() },
    ]
}

#[derive(serde::Serialize)]
struct Subject { id: String, name: String, color: String }

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![ping, get_subjects])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

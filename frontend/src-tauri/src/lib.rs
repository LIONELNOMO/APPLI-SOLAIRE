//! Version PC de DimSolaire.
//!
//! Tauri réserve un port libre, génère un jeton de session, lance le moteur
//! de calcul Python en sidecar, puis transmet l'adresse et le jeton à
//! l'interface. Le sidecar est arrêté à la fermeture de la fenêtre.

use std::{
    fs,
    net::TcpListener,
    path::PathBuf,
    sync::{Arc, Mutex},
};

use tauri::{Manager, RunEvent, State};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

/// État partagé : adresse de l'API, jeton de session et processus du moteur.
struct Moteur {
    base_url: String,
    token: String,
    journal: PathBuf,
    enfant: Arc<Mutex<Option<CommandChild>>>,
}

#[derive(serde::Serialize)]
struct ConfigApi {
    base_url: String,
    token: String,
    journal: String,
}

/// Transmet à l'interface de quoi joindre le moteur de calcul.
#[tauri::command]
fn api_config(moteur: State<'_, Moteur>) -> ConfigApi {
    ConfigApi {
        base_url: moteur.base_url.clone(),
        token: moteur.token.clone(),
        journal: moteur.journal.to_string_lossy().into_owned(),
    }
}

/// Réserve un port libre, puis le libère aussitôt pour le passer au sidecar.
///
/// La fenêtre entre la libération et l'écoute du moteur est de quelques
/// millisecondes : le risque de collision est négligeable sur un poste.
fn port_libre() -> Result<u16, std::io::Error> {
    let ecouteur = TcpListener::bind("127.0.0.1:0")?;
    let port = ecouteur.local_addr()?.port();
    drop(ecouteur);
    Ok(port)
}

fn jeton_aleatoire() -> String {
    uuid::Uuid::new_v4().simple().to_string()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let application = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            let port = port_libre()?;
            let token = jeton_aleatoire();

            let dossier = app.path().app_data_dir()?;
            let dossier_journaux = dossier.join("logs");
            fs::create_dir_all(&dossier_journaux)?;
            let journal = dossier_journaux.join("api.log");
            let base_de_donnees = dossier.join("dimsolaire.db");

            let arguments = vec![
                "--port".to_string(),
                port.to_string(),
                "--db".to_string(),
                base_de_donnees.to_string_lossy().into_owned(),
                "--parent-pid".to_string(),
                std::process::id().to_string(),
                "--log".to_string(),
                journal.to_string_lossy().into_owned(),
            ];

            let (mut flux, enfant) = app
                .shell()
                .sidecar("dimsolaire-api")?
                .args(arguments)
                .env("DIMSOLAIRE_TOKEN", &token)
                .spawn()?;

            // La sortie du sidecar doit être consommée : un tube saturé
            // bloquerait le processus Python au premier message volumineux.
            tauri::async_runtime::spawn(async move {
                while flux.recv().await.is_some() {}
            });

            app.manage(Moteur {
                base_url: format!("http://127.0.0.1:{port}"),
                token,
                journal,
                enfant: Arc::new(Mutex::new(Some(enfant))),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![api_config])
        .build(tauri::generate_context!())
        .expect("échec du démarrage de DimSolaire");

    application.run(|gestionnaire, evenement| {
        if let RunEvent::Exit = evenement {
            // Arrêt explicite : le moteur surveille aussi notre PID, mais
            // ce chemin est le plus rapide et le plus propre.
            if let Some(moteur) = gestionnaire.try_state::<Moteur>() {
                if let Ok(mut verrou) = moteur.enfant.lock() {
                    if let Some(processus) = verrou.take() {
                        let _ = processus.kill();
                    }
                }
            }
        }
    });
}

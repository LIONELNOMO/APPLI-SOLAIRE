// La fenêtre console est masquée en production, mais conservée en débogage
// pour voir la sortie du moteur de calcul.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    dimsolaire_lib::run()
}

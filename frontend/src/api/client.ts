/**
 * Client HTTP du moteur de calcul.
 *
 * En version PC, l'adresse et le jeton sont fournis par Tauri au démarrage.
 * En version web, l'API est servie par la même origine que l'interface.
 */

export interface ConfigApi {
  baseUrl: string;
  token?: string;
  journal?: string;
}

interface ReponseTauri {
  base_url: string;
  token: string;
  journal: string;
}

let cache: ConfigApi | null = null;

/** Vrai lorsque l'interface tourne dans la fenêtre Tauri. */
function dansTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

async function config(): Promise<ConfigApi> {
  if (cache) return cache;

  if (dansTauri()) {
    const { invoke } = await import("@tauri-apps/api/core");
    const brut = await invoke<ReponseTauri>("api_config");
    cache = {
      baseUrl: brut.base_url,
      token: brut.token,
      journal: brut.journal,
    };
  } else {
    // Chaîne vide en version web : même origine, aucun préfixe.
    cache = { baseUrl: import.meta.env.VITE_API_URL ?? "" };
  }
  return cache;
}

export class ErreurApi extends Error {
  readonly statut: number;
  readonly detail: unknown;

  constructor(statut: number, detail: unknown, message: string) {
    super(message);
    this.name = "ErreurApi";
    this.statut = statut;
    this.detail = detail;
  }
}

/** Message lisible extrait du corps d'une réponse en erreur. */
function messageErreur(statut: number, detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const objet = detail as Record<string, unknown>;
    if (typeof objet.message === "string") return objet.message;
  }
  if (statut === 401) return "Jeton de session invalide";
  if (statut === 404) return "Ressource introuvable";
  if (statut === 409) return "Conflit : la ressource existe déjà";
  if (statut === 422) return "Données invalides";
  return `Erreur ${statut}`;
}

async function requete(
  chemin: string,
  options: RequestInit = {},
): Promise<Response> {
  const { baseUrl, token } = await config();
  const entetes = new Headers(options.headers);
  if (options.body && !entetes.has("Content-Type")) {
    entetes.set("Content-Type", "application/json");
  }
  if (token) entetes.set("X-App-Token", token);

  const reponse = await fetch(`${baseUrl}/api/v1${chemin}`, {
    ...options,
    headers: entetes,
  });

  if (!reponse.ok) {
    let detail: unknown = null;
    try {
      const charge = await reponse.json();
      detail = (charge as { detail?: unknown }).detail ?? charge;
    } catch {
      detail = await reponse.text().catch(() => null);
    }
    throw new ErreurApi(
      reponse.status,
      detail,
      messageErreur(reponse.status, detail),
    );
  }
  return reponse;
}

export async function apiGet<T>(chemin: string): Promise<T> {
  const reponse = await requete(chemin);
  return reponse.json() as Promise<T>;
}

export async function apiPost<T>(chemin: string, corps?: unknown): Promise<T> {
  const reponse = await requete(chemin, {
    method: "POST",
    body: corps === undefined ? undefined : JSON.stringify(corps),
  });
  return reponse.status === 204
    ? (undefined as T)
    : (reponse.json() as Promise<T>);
}

export async function apiPut<T>(chemin: string, corps: unknown): Promise<T> {
  const reponse = await requete(chemin, {
    method: "PUT",
    body: JSON.stringify(corps),
  });
  return reponse.json() as Promise<T>;
}

export async function apiDelete(chemin: string): Promise<void> {
  await requete(chemin, { method: "DELETE" });
}

/** Télécharge un fichier binaire, par exemple le rapport PDF. */
export async function apiBlob(
  chemin: string,
  corps?: unknown,
): Promise<{ blob: Blob; nomFichier: string }> {
  const reponse = await requete(chemin, {
    method: corps === undefined ? "GET" : "POST",
    body: corps === undefined ? undefined : JSON.stringify(corps),
  });

  const disposition = reponse.headers.get("Content-Disposition") ?? "";
  // `filename*` en UTF-8 est prioritaire sur `filename` en ASCII (RFC 6266).
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  const ascii = /filename="([^"]+)"/i.exec(disposition);
  const nomFichier = utf8
    ? decodeURIComponent(utf8[1])
    : (ascii?.[1] ?? "telechargement");

  return { blob: await reponse.blob(), nomFichier };
}

/**
 * Attend que le moteur réponde. En version PC, le sidecar met une à trois
 * secondes à démarrer ; au-delà du délai, l'interface propose de réessayer.
 */
export async function attendreApi(delaiMs = 30_000): Promise<boolean> {
  const limite = Date.now() + delaiMs;
  while (Date.now() < limite) {
    try {
      const { baseUrl } = await config();
      const reponse = await fetch(`${baseUrl}/api/v1/health`);
      if (reponse.ok) return true;
    } catch {
      // Le moteur n'écoute pas encore.
    }
    await new Promise((resoudre) => setTimeout(resoudre, 250));
  }
  return false;
}

/** Chemin du journal du moteur, pour le message d'échec de démarrage. */
export async function cheminJournal(): Promise<string | undefined> {
  return (await config()).journal;
}

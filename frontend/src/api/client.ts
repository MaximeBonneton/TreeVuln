const API_BASE = '/api/v1';

/**
 * Événement émis lorsqu'une requête reçoit un 401 (session expirée ou
 * invalide). App.tsx l'écoute pour revenir à l'écran de login. Découplé
 * (event global) pour éviter que la couche API ne dépende de l'UI.
 */
export const AUTH_UNAUTHORIZED_EVENT = 'auth:unauthorized';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * FastAPI renvoie les erreurs de validation (422) sous forme d'un tableau
 * d'objets `{loc, msg, type}`. On les met en forme en un message lisible
 * « champ: message » plutôt que d'afficher « [object Object] ».
 */
function formatErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const loc = Array.isArray((item as { loc?: unknown[] }).loc)
            ? (item as { loc: unknown[] }).loc
                .filter((p) => p !== 'body')
                .join('.')
            : '';
          const msg = (item as { msg: string }).msg;
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join('; ');
  }
  return 'Request failed';
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const config: RequestInit = {
    ...options,
    headers,
    credentials: 'same-origin',
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    // F-5 : une session expirée/invalide ramène l'utilisateur au login.
    // Exclut les endpoints d'auth eux-mêmes : un 401 de /auth/login est un
    // mauvais mot de passe, pas une session expirée (l'écran de login gère
    // déjà l'erreur).
    if (response.status === 401 && !endpoint.startsWith('/auth/')) {
      window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
    }
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, formatErrorDetail(error.detail));
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint),

  post: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),
};

/**
 * Retourne les headers d'authentification pour les appels fetch directs
 * (uploads de fichiers, exports blob, etc.).
 * L'authentification est gérée par cookies HttpOnly (credentials: same-origin).
 */
export function getAuthHeaders(): Record<string, string> {
  return {};
}

export { ApiError };

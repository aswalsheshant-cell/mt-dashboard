import type { Layout } from '@mt-dashboard/layout-schema';
import { importLayout, SCHEMA_VERSION } from '@mt-dashboard/layout-schema';

const STORAGE_KEY = 'layout-studio-autosave';
const SCHEMA_KEY = 'layout-studio-schema-version';

/** Debounce timer for autosave (ms) */
const DEBOUNCE_MS = 2000;

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

/** Trigger a debounced autosave. Clears any pending save first. */
export function scheduleAutosave(layout: Layout): void {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    saveLayout(layout);
    debounceTimer = null;
  }, DEBOUNCE_MS);
}

/** Immediately save layout to localStorage. Rejects secrets. */
export function saveLayout(layout: Layout): { ok: boolean; error?: string } {
  try {
    const json = JSON.stringify(layout);
    // Never autosave secrets
    const secretPatterns = [/sk-[A-Za-z0-9]{20,}/, /ghp_[A-Za-z0-9]{36}/, /Bearer\s+[A-Za-z0-9+/=]{20,}/];
    for (const p of secretPatterns) {
      if (p.test(json)) {
        return { ok: false, error: 'Autosave blocked: potential secret in layout data.' };
      }
    }
    localStorage.setItem(STORAGE_KEY, json);
    localStorage.setItem(SCHEMA_KEY, SCHEMA_VERSION);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: `Autosave failed: ${(e as Error).message}` };
  }
}

/** Load layout from localStorage. Returns null if nothing saved or invalid. */
export function loadSavedLayout(): Layout | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const result = importLayout(raw);
    if (!result.success) {
      console.warn('Autosave recovery failed — invalid schema:', result.errors);
      return null;
    }
    return result.data;
  } catch (e) {
    console.warn('Autosave load failed:', e);
    return null;
  }
}

/** Clear saved draft */
export function clearSavedLayout(): void {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(SCHEMA_KEY);
}

/** Returns true if a saved draft exists */
export function hasSavedLayout(): boolean {
  return localStorage.getItem(STORAGE_KEY) !== null;
}

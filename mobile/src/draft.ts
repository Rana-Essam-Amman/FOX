export type Duration = '15s' | '30s' | '60s';
export type VisualStyle = 'cinematic' | 'dynamic' | 'minimal';
export type Aspect = '16:9' | '9:16' | '1:1';

export interface LocalDraft {
  prompt: string;
  imageUri: string | null;
  duration: Duration;
  style: VisualStyle;
  aspect: Aspect;
}

let currentDraft: LocalDraft | null = null;

export function setLocalDraft(draft: LocalDraft): void {
  currentDraft = draft;
}

export function getLocalDraft(): LocalDraft | null {
  return currentDraft;
}

export function clearLocalDraft(): void {
  currentDraft = null;
}

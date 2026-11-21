import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';

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

const DRAFT_KEY = '@fox/localDraft';
const DRAFT_MEDIA_DIR = `${FileSystem.documentDirectory}draft-media/`;

async function ensureMediaDir(): Promise<void> {
  const info = await FileSystem.getInfoAsync(DRAFT_MEDIA_DIR);
  if (!info.exists) {
    await FileSystem.makeDirectoryAsync(DRAFT_MEDIA_DIR, { intermediates: true });
  }
}

function isTemporaryUri(uri: string): boolean {
  return uri.startsWith('file://') || uri.startsWith('content://') || uri.includes('/tmp/') || uri.includes('ImagePicker');
}

async function persistImageIfTemporary(uri: string | null): Promise<string | null> {
  if (!uri) return null;
  if (!isTemporaryUri(uri)) return uri;

  try {
    await ensureMediaDir();
    const ext = uri.split('.').pop()?.split('?')[0] || 'jpg';
    const dest = `${DRAFT_MEDIA_DIR}ref-${Date.now()}.${ext}`;
    await FileSystem.copyAsync({ from: uri, to: dest });
    return dest;
  } catch {
    return null;
  }
}

export async function setLocalDraft(draft: LocalDraft): Promise<void> {
  const permanentImage = await persistImageIfTemporary(draft.imageUri);
  const toStore: LocalDraft = {
    ...draft,
    imageUri: permanentImage,
  };
  await AsyncStorage.setItem(DRAFT_KEY, JSON.stringify(toStore));
}

export async function getLocalDraft(): Promise<LocalDraft | null> {
  try {
    const raw = await AsyncStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LocalDraft;
    if (parsed.imageUri) {
      const info = await FileSystem.getInfoAsync(parsed.imageUri);
      if (!info.exists) {
        parsed.imageUri = null;
      }
    }
    return parsed;
  } catch {
    return null;
  }
}

export async function clearLocalDraft(): Promise<void> {
  await AsyncStorage.removeItem(DRAFT_KEY);
  try {
    await FileSystem.deleteAsync(DRAFT_MEDIA_DIR, { idempotent: true });
  } catch {
    // ignore
  }
}

let memoryDraft: LocalDraft | null = null;

export function getMemoryDraft(): LocalDraft | null {
  return memoryDraft;
}

export function setMemoryDraft(draft: LocalDraft | null): void {
  memoryDraft = draft;
}

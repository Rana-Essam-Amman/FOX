import { setLocalDraft, getLocalDraft, clearLocalDraft } from './draft';

const mockStore = new Map<string, string>();
jest.mock('@react-native-async-storage/async-storage', () => ({
  setItem: async (k: string, v: string) => { mockStore.set(k, v); },
  getItem: async (k: string) => mockStore.get(k) ?? null,
  removeItem: async (k: string) => { mockStore.delete(k); },
}));

jest.mock('expo-file-system/legacy', () => ({
  documentDirectory: 'file:///mock/',
  getInfoAsync: jest.fn(async () => ({ exists: true })),
  makeDirectoryAsync: jest.fn(async () => undefined),
  copyAsync: jest.fn(async () => undefined),
  deleteAsync: jest.fn(async () => undefined),
}));

describe('local draft persistence', () => {
  beforeEach(async () => {
    mockStore.clear();
    await clearLocalDraft();
  });

  it('persists and recovers a draft', async () => {
    const draft = {
      prompt: 'test idea',
      imageUri: null,
      duration: '30s' as const,
      style: 'cinematic' as const,
      aspect: '9:16' as const,
    };
    await setLocalDraft(draft);
    const recovered = await getLocalDraft();
    expect(recovered?.prompt).toBe('test idea');
    expect(recovered?.duration).toBe('30s');
  });

  it('clears the draft', async () => {
    await setLocalDraft({
      prompt: 'x',
      imageUri: null,
      duration: '15s',
      style: 'minimal',
      aspect: '1:1',
    });
    await clearLocalDraft();
    expect(await getLocalDraft()).toBeNull();
  });
});

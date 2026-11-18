import { detectLocale, setupI18n, i18n, isRTL, loadSavedLocale, saveLocale, initializeLocale } from './index';
import { getLocales } from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';

jest.mock('expo-localization', () => ({
  getLocales: jest.fn(() => [{ languageCode: 'en', languageTag: 'en-US' }]),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(() => Promise.resolve(null)),
  setItem: jest.fn(() => Promise.resolve()),
}));

const mockedGetLocales = getLocales as jest.MockedFunction<typeof getLocales>;
const mockedStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>;

describe('i18n locale detection and persistence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedGetLocales.mockReturnValue([{ languageCode: 'en', languageTag: 'en-US' } as never]);
    setupI18n('en');
  });

  it('detects Arabic device locale', () => {
    mockedGetLocales.mockReturnValue([{ languageCode: 'ar', languageTag: 'ar-SA' } as never]);
    expect(detectLocale()).toBe('ar');
  });

  it('detects English device locale', () => {
    mockedGetLocales.mockReturnValue([{ languageCode: 'en', languageTag: 'en-US' } as never]);
    expect(detectLocale()).toBe('en');
  });

  it('falls back to English for unsupported device locale', () => {
    mockedGetLocales.mockReturnValue([{ languageCode: 'fr', languageTag: 'fr-FR' } as never]);
    expect(detectLocale()).toBe('en');
  });

  it('falls back when locale code missing', () => {
    mockedGetLocales.mockReturnValue([{ languageCode: undefined } as never]);
    expect(detectLocale()).toBe('en');
  });

  it('restores saved Arabic selection', async () => {
    mockedStorage.getItem.mockResolvedValue('ar');
    const saved = await loadSavedLocale();
    expect(saved).toBe('ar');
    expect(mockedStorage.getItem).toHaveBeenCalledWith('@fox_locale');
  });

  it('restores saved English selection', async () => {
    mockedStorage.getItem.mockResolvedValue('en');
    const saved = await loadSavedLocale();
    expect(saved).toBe('en');
  });

  it('falls back to null for invalid saved value', async () => {
    mockedStorage.getItem.mockResolvedValue('fr');
    const saved = await loadSavedLocale();
    expect(saved).toBeNull();
  });

  it('handles storage load failure safely', async () => {
    mockedStorage.getItem.mockRejectedValue(new Error('storage error'));
    const saved = await loadSavedLocale();
    expect(saved).toBeNull();
  });

  it('initializeLocale prefers saved over device', async () => {
    mockedStorage.getItem.mockResolvedValue('ar');
    mockedGetLocales.mockReturnValue([{ languageCode: 'en' } as never]);
    const locale = await initializeLocale();
    expect(locale).toBe('ar');
    expect(i18n.locale).toBe('ar');
    expect(isRTL()).toBe(true);
  });

  it('initializeLocale falls back to device locale when no saved', async () => {
    mockedStorage.getItem.mockResolvedValue(null);
    mockedGetLocales.mockReturnValue([{ languageCode: 'ar' } as never]);
    const locale = await initializeLocale();
    expect(locale).toBe('ar');
    expect(isRTL()).toBe(true);
  });

  it('saves locale', async () => {
    mockedStorage.setItem.mockResolvedValue(undefined as never);
    await saveLocale('ar');
    expect(mockedStorage.setItem).toHaveBeenCalledWith('@fox_locale', 'ar');
  });

  it('handles storage save failure safely', async () => {
    mockedStorage.setItem.mockRejectedValue(new Error('fail'));
    await expect(saveLocale('en')).resolves.toBeUndefined();
  });

  it('falls back to English for missing translation key', () => {
    setupI18n('ar');
    const missing = i18n.t('nonexistent.key');
    expect(typeof missing).toBe('string');
    setupI18n('en');
    expect(i18n.t('home.title')).toBe('FOX');
  });

  it('Arabic means RTL and English means LTR', () => {
    setupI18n('ar');
    expect(isRTL()).toBe(true);
    setupI18n('en');
    expect(isRTL()).toBe(false);
  });
});

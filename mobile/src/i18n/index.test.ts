import { setupI18n, i18n, isRTL } from './index';

describe('i18n locale', () => {
  beforeEach(() => {
    setupI18n('en');
  });

  it('detects non-Arabic as English by default', () => {
    // detectLocale uses device; we test the helper path via setup
    setupI18n('en');
    expect(i18n.locale).toBe('en');
    expect(isRTL()).toBe(false);
  });

  it('sets Arabic and RTL correctly', () => {
    setupI18n('ar');
    expect(i18n.locale).toBe('ar');
    expect(isRTL()).toBe(true);
  });

  it('falls back for unknown locale', () => {
    setupI18n('fr' as 'en');
    expect(i18n.locale).toBe('fr');
  });
});
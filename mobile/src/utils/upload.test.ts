import { validateImageUpload } from './upload';
import { setupI18n, i18n } from '../i18n';

describe('validateImageUpload', () => {
  beforeEach(() => {
    setupI18n('en');
  });

  it('rejects empty uri', () => {
    const result = validateImageUpload('');
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('missing_uri');
  });

  it('rejects missing uri', () => {
    const result = validateImageUpload(null);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('missing_uri');
  });

  it('accepts valid JPEG', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', 1024);
    expect(result.valid).toBe(true);
    expect(result.errorCode).toBeUndefined();
  });

  it('accepts valid PNG', () => {
    const result = validateImageUpload('file://photo.png', 'image/png', 2048);
    expect(result.valid).toBe(true);
  });

  it('accepts valid WebP', () => {
    const result = validateImageUpload('file://photo.webp', 'image/webp', 512);
    expect(result.valid).toBe(true);
  });

  it('rejects unsupported MIME', () => {
    const result = validateImageUpload('file://doc.pdf', 'application/pdf', 1024);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('unsupported_mime');
  });

  it('rejects missing MIME', () => {
    const result = validateImageUpload('file://photo.jpg', null, 1024);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('missing_mime');
  });

  it('rejects missing size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', null);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('missing_size');
  });

  it('rejects zero size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', 0);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('invalid_size');
  });

  it('rejects negative size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', -100);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('invalid_size');
  });

  it('rejects non-finite size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', Number.NaN);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('invalid_size');
  });

  it('accepts exact maximum size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', 10 * 1024 * 1024);
    expect(result.valid).toBe(true);
  });

  it('rejects oversized image', () => {
    const result = validateImageUpload('file://big.jpg', 'image/jpeg', 11 * 1024 * 1024);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('too_large');
  });

  it('rejects empty asset', () => {
    const result = validateImageUpload('', '', 0);
    expect(result.valid).toBe(false);
    expect(result.errorCode).toBe('missing_uri');
  });

  describe('localized error messages', () => {
    const cases: { code: 'missing_uri' | 'unsupported_mime' | 'too_large'; en: string; ar: string }[] = [
      { code: 'missing_uri', en: 'No file selected', ar: 'لم يتم اختيار ملف' },
      { code: 'unsupported_mime', en: 'Unsupported image type', ar: 'نوع الصورة غير مدعوم' },
      { code: 'too_large', en: 'under 10MB', ar: 'أقل من 10 ميجابايت' },
    ];

    it.each(cases)('translates $code in English', ({ code, en }) => {
      setupI18n('en');
      const msg = i18n.t(`create.errors.${code}`);
      expect(msg).toContain(en);
    });

    it.each(cases)('translates $code in Arabic', ({ code, ar }) => {
      setupI18n('ar');
      const msg = i18n.t(`create.errors.${code}`);
      expect(msg).toContain(ar);
    });

    it('falls back for unknown code', () => {
      setupI18n('en');
      const msg = i18n.t('create.errors.unknown');
      expect(msg).toBe('An unknown validation error occurred.');
      setupI18n('ar');
      expect(i18n.t('create.errors.unknown')).toContain('غير معروف');
    });
  });
});

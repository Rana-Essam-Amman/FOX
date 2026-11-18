import { validateImageUpload } from './upload';

describe('validateImageUpload', () => {
  it('rejects empty uri', () => {
    const result = validateImageUpload('');
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/empty|No file/i);
  });

  it('rejects missing uri', () => {
    const result = validateImageUpload(null as unknown as string);
    expect(result.valid).toBe(false);
  });

  it('accepts valid JPEG', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', 1024);
    expect(result.valid).toBe(true);
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
    expect(result.error).toMatch(/Unsupported/i);
  });

  it('rejects missing MIME', () => {
    const result = validateImageUpload('file://photo.jpg', null, 1024);
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/missing MIME|could not be verified/i);
  });

  it('rejects missing size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', null);
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/missing|size/i);
  });

  it('rejects zero size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', 0);
    expect(result.valid).toBe(false);
  });

  it('rejects negative size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', -100);
    expect(result.valid).toBe(false);
  });

  it('rejects non-finite size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', Number.NaN);
    expect(result.valid).toBe(false);
  });

  it('accepts exact maximum size', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', 10 * 1024 * 1024);
    expect(result.valid).toBe(true);
  });

  it('rejects oversized image', () => {
    const result = validateImageUpload('file://big.jpg', 'image/jpeg', 11 * 1024 * 1024);
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/10MB/i);
  });

  it('rejects empty asset', () => {
    const result = validateImageUpload('', '', 0);
    expect(result.valid).toBe(false);
  });
});
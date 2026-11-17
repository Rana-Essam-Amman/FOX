import { validateImageUpload } from './upload';

describe('validateImageUpload', () => {
  it('rejects empty uri', () => {
    const result = validateImageUpload('');
    expect(result.valid).toBe(false);
  });

  it('accepts valid image', () => {
    const result = validateImageUpload('file://photo.jpg', 'image/jpeg', 1024);
    expect(result.valid).toBe(true);
  });

  it('rejects oversized image', () => {
    const result = validateImageUpload('file://big.jpg', 'image/jpeg', 11 * 1024 * 1024);
    expect(result.valid).toBe(false);
    expect(result.error).toContain('10MB');
  });

  it('rejects invalid type', () => {
    const result = validateImageUpload('file://doc.pdf', 'application/pdf', 1024);
    expect(result.valid).toBe(false);
  });
});
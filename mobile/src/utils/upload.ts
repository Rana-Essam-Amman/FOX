import { UploadValidationResult, UploadErrorCode } from '../models';

const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif']);

export function validateImageUpload(
  uri: string | null | undefined,
  mimeType?: string | null | undefined,
  fileSize?: number | null | undefined
): UploadValidationResult {
  if (uri == null || uri.trim() === '') {
    return { valid: false, errorCode: 'missing_uri' };
  }

  if (mimeType == null || mimeType.trim() === '') {
    return { valid: false, errorCode: 'missing_mime' };
  }

  if (!ALLOWED_TYPES.has(mimeType)) {
    return { valid: false, errorCode: 'unsupported_mime' };
  }

  if (fileSize == null) {
    return { valid: false, errorCode: 'missing_size' };
  }

  if (typeof fileSize !== 'number' || !Number.isFinite(fileSize) || fileSize <= 0) {
    return { valid: false, errorCode: 'invalid_size' };
  }

  if (fileSize > MAX_IMAGE_SIZE) {
    return { valid: false, errorCode: 'too_large' };
  }

  return { valid: true };
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getUploadErrorMessage(code: UploadErrorCode | undefined): string {
  if (!code) return '';
  // Fallback key if translation missing; i18n.enableFallback handles English
  return code;
}

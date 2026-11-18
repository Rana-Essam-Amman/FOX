import { UploadValidationResult } from '../models';

const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif']);

export function validateImageUpload(
  uri: string | null | undefined,
  mimeType?: string | null | undefined,
  fileSize?: number | null | undefined
): UploadValidationResult {
  if (uri == null || uri.trim() === '') {
    return { valid: false, error: 'No file selected or URI is empty.' };
  }

  if (mimeType == null || mimeType.trim() === '') {
    return { valid: false, error: 'Image type could not be verified (missing MIME type).' };
  }

  if (!ALLOWED_TYPES.has(mimeType)) {
    return { valid: false, error: `Unsupported image type: ${mimeType}. Supported: JPEG, PNG, WebP, GIF.` };
  }

  if (fileSize == null) {
    return { valid: false, error: 'Image size is missing and could not be verified.' };
  }

  if (typeof fileSize !== 'number' || !Number.isFinite(fileSize) || fileSize <= 0) {
    return { valid: false, error: 'Image size is invalid (must be a positive finite number).' };
  }

  if (fileSize > MAX_IMAGE_SIZE) {
    return { valid: false, error: 'Image must be under 10MB.' };
  }

  return { valid: true };
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
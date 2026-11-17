import { UploadValidationResult } from '../models';

const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

export function validateImageUpload(
  uri: string,
  mimeType?: string,
  fileSize?: number
): UploadValidationResult {
  if (!uri) {
    return { valid: false, error: 'No file selected' };
  }

  if (mimeType && !ALLOWED_TYPES.includes(mimeType)) {
    return { valid: false, error: 'Please select a valid image file (JPEG, PNG, WebP, GIF).' };
  }

  if (fileSize && fileSize > MAX_IMAGE_SIZE) {
    return { valid: false, error: 'Image must be under 10MB.' };
  }

  return { valid: true };
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
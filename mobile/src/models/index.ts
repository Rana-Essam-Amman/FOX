export interface Project {
  id: string;
  title: string;
  createdAt: string;
  thumbnailUrl?: string;
  status: 'draft' | 'processing' | 'completed' | 'failed';
}

export interface VideoCreationInput {
  prompt: string;
  imageUri?: string;
  duration: '15s' | '30s' | '60s';
  style: 'cinematic' | 'dynamic' | 'minimal';
}

export interface UploadValidationResult {
  valid: boolean;
  error?: string;
}
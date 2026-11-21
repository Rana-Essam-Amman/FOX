export type Duration = '15s' | '30s' | '60s';
export type VisualStyle = 'cinematic' | 'dynamic' | 'minimal';
export type Aspect = '16:9' | '9:16' | '1:1';

export interface LocalDraft {
  prompt: string;
  imageUri: string | null;
  duration: Duration;
  style: VisualStyle;
  aspect: Aspect;
}

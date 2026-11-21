import type { FoxApiClient } from './client';
import type {
  CreateTaskRequest,
  CreateTaskResult,
  TaskStatusResult,
  UploadResult,
} from './types';

function kindToPath(kind: CreateTaskRequest['kind']): string {
  switch (kind) {
    case 'video':
      return '/api/v1/videos';
    case 'subtitle':
      return '/api/v1/subtitle';
    case 'audio':
      return '/api/v1/audio';
    default:
      return '/api/v1/videos';
  }
}

/**
 * Create a generation task through the gateway.
 * Provider secrets stay server-side; the client only sends user input.
 */
export async function createTask(
  client: FoxApiClient,
  input: CreateTaskRequest
): Promise<CreateTaskResult> {
  const data = await client.requestData<{ task_id?: string; taskId?: string }>({
    method: 'POST',
    path: kindToPath(input.kind),
    body: {
      video_subject: input.prompt,
      video_aspect: input.aspect,
      video_style: input.style,
      video_language: input.language,
      material_id: input.materialId,
      duration: input.duration,
    },
  });
  const taskId = data.task_id ?? data.taskId;
  if (!taskId) {
    throw new Error('Task response missing task id');
  }
  return { taskId };
}

export async function getTaskStatus(
  client: FoxApiClient,
  taskId: string
): Promise<TaskStatusResult> {
  const data = await client.requestData<{
    task_id?: string;
    state?: number | string;
    status?: string;
    progress?: number;
    error?: string;
    videos?: string[];
  }>({
    method: 'GET',
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}`,
  });

  return {
    taskId: data.task_id ?? taskId,
    status: normalizeStatus(data.state ?? data.status),
    progress: data.progress,
    errorMessage: data.error,
    resultUrls: data.videos,
    resultUrl: data.videos?.[0],
  };
}

export async function cancelTask(
  client: FoxApiClient,
  taskId: string
): Promise<void> {
  await client.request({
    method: 'DELETE',
    path: `/api/v1/tasks/${encodeURIComponent(taskId)}`,
  });
}

/**
 * Upload a local file URI to the gateway. The server returns a material id.
 * Temporary client URIs must not be treated as permanent server paths.
 */
export async function uploadMaterial(
  client: FoxApiClient,
  localUri: string,
  mimeType: string,
  fileName = 'upload.jpg'
): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', {
    uri: localUri,
    name: fileName,
    type: mimeType,
  } as unknown as Blob);

  const data = await client.requestData<{
    material_id?: string;
    materialId?: string;
    content_type?: string;
    size?: number;
  }>({
    method: 'POST',
    path: '/api/v1/materials',
    formData: form,
  });

  const materialId = data.material_id ?? data.materialId;
  if (!materialId) {
    throw new Error('Upload response missing material id');
  }
  return {
    materialId,
    contentType: data.content_type,
    size: data.size,
  };
}

function normalizeStatus(raw: number | string | undefined): TaskStatusResult['status'] {
  if (raw === undefined || raw === null) return 'pending';
  if (typeof raw === 'string') {
    const lower = raw.toLowerCase();
    if (['pending', 'processing', 'completed', 'failed', 'cancelled'].includes(lower)) {
      return lower as TaskStatusResult['status'];
    }
  }
  const n = Number(raw);
  if (n === 0) return 'pending';
  if (n === 1) return 'processing';
  if (n === 2) return 'completed';
  if (n === 3) return 'failed';
  return 'pending';
}

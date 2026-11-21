import {
  FoxApiClient,
  getApiClient,
  resetApiClient,
  createTask,
  getTaskStatus,
  ApiError,
  isApiConfigured,
  resolveApiConfig,
} from './index';

describe('API config', () => {
  it('treats empty base URL as not configured', () => {
    const config = resolveApiConfig({ baseUrl: '' });
    expect(isApiConfigured(config)).toBe(false);
  });

  it('strips trailing slash from base URL', () => {
    const config = resolveApiConfig({ baseUrl: 'https://example.com/api/' });
    expect(config.baseUrl).toBe('https://example.com/api');
  });
});

describe('FoxApiClient', () => {
  afterEach(() => {
    resetApiClient();
    jest.restoreAllMocks();
  });

  it('throws not_configured when base URL is missing', async () => {
    const client = new FoxApiClient({ baseUrl: '' });
    await expect(
      client.request({ path: '/api/v1/tasks/1' })
    ).rejects.toMatchObject({ code: 'not_configured' });
  });

  it('attaches Authorization when token provider is set', async () => {
    const fetchMock = jest.fn(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ status: 200, data: { ok: true } }),
    }));
    // @ts-expect-error test double
    global.fetch = fetchMock;

    const client = new FoxApiClient({
      baseUrl: 'https://gateway.test',
      getAccessToken: () => 'user-token-1',
    });
    await client.request({ path: '/api/v1/ping' });

    expect(fetchMock).toHaveBeenCalled();
    const callArgs = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const init = callArgs[1];
    expect((init.headers as Record<string, string>).Authorization).toBe(
      'Bearer user-token-1'
    );
  });

  it('maps 401 to unauthorized', async () => {
    // @ts-expect-error test double
    global.fetch = jest.fn(async () => ({
      ok: false,
      status: 401,
      text: async () => JSON.stringify({ message: 'invalid token' }),
    }));

    const client = new FoxApiClient({ baseUrl: 'https://gateway.test' });
    await expect(client.request({ path: '/x' })).rejects.toBeInstanceOf(ApiError);
    await expect(client.request({ path: '/x' })).rejects.toMatchObject({
      code: 'unauthorized',
      status: 401,
    });
  });

  it('createTask returns task id from gateway envelope', async () => {
    // @ts-expect-error test double
    global.fetch = jest.fn(async () => ({
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({ status: 200, data: { task_id: 'task-abc' } }),
    }));

    const client = new FoxApiClient({ baseUrl: 'https://gateway.test' });
    const result = await createTask(client, {
      kind: 'video',
      prompt: 'a product demo',
    });
    expect(result.taskId).toBe('task-abc');
  });

  it('getTaskStatus normalizes numeric legacy states', async () => {
    // @ts-expect-error test double
    global.fetch = jest.fn(async () => ({
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({
          status: 200,
          data: { task_id: 't1', state: 2, videos: ['https://cdn/v.mp4'] },
        }),
    }));

    const client = new FoxApiClient({ baseUrl: 'https://gateway.test' });
    const status = await getTaskStatus(client, 't1');
    expect(status.status).toBe('completed');
    expect(status.resultUrl).toBe('https://cdn/v.mp4');
  });

  it('getApiClient returns a shared instance by default', () => {
    resetApiClient();
    const a = getApiClient({ baseUrl: 'https://a.test' });
    const b = getApiClient();
    expect(a).toBe(b);
  });
});

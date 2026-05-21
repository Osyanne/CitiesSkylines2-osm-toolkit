// Mock fetch implementation for unit tests.
// Usage: const fetch = mockFetch([{ url: /pattern/, status: 200, body: {...} }]);

export function mockFetch(responses) {
  const calls = [];
  const fn = async (url, options = {}) => {
    calls.push({ url, options });
    const match = responses.find(r => r.url.test(url));
    if (!match) {
      throw new Error(`No mock response for ${url}`);
    }
    return {
      ok: match.status >= 200 && match.status < 300,
      status: match.status,
      statusText: match.statusText || (match.status === 200 ? 'OK' : 'Error'),
      json: async () => match.body,
      text: async () => typeof match.body === 'string' ? match.body : JSON.stringify(match.body),
      blob: async () => new Blob([match.body]),
      arrayBuffer: async () => new ArrayBuffer(8)
    };
  };
  fn.calls = calls;
  return fn;
}

import http from 'node:http';
import https from 'node:https';
import { spawn } from 'node:child_process';

const PROXY_PORT = Number(process.env.PROXY_PORT ?? 5000);
const FLUTTER_PORT = Number(process.env.FLUTTER_PORT ?? 5001);
const TARGET = new URL(process.env.TARGET ?? 'https://sai-seeds-preprod.onrender.com');

const API_PREFIXES = ['/api/', '/android/'];

const isApi = (url) => API_PREFIXES.some((prefix) => url.startsWith(prefix));

const stripDomain = (cookie) =>
  cookie
    .split(';')
    .filter((part) => !/^\s*domain=/i.test(part))
    .filter((part) => !/^\s*secure\s*$/i.test(part))
    .join(';');

const proxyToApi = (req, res) => {
  const headers = { ...req.headers, host: TARGET.host };
  delete headers['accept-encoding'];

  if (headers.origin) headers.origin = TARGET.origin;
  if (headers.referer) {
    headers.referer = headers.referer.replace(
      `http://localhost:${PROXY_PORT}`,
      TARGET.origin,
    );
  }

  const upstream = https.request(
    {
      protocol: TARGET.protocol,
      hostname: TARGET.hostname,
      port: TARGET.port || 443,
      path: req.url,
      method: req.method,
      headers,
    },
    (upstreamRes) => {
      const outHeaders = { ...upstreamRes.headers };

      const setCookie = upstreamRes.headers['set-cookie'];
      if (setCookie) outHeaders['set-cookie'] = setCookie.map(stripDomain);

      delete outHeaders['access-control-allow-origin'];
      delete outHeaders['access-control-allow-credentials'];

      res.writeHead(upstreamRes.statusCode ?? 502, outHeaders);
      upstreamRes.pipe(res);
    },
  );

  upstream.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'text/plain' });
    res.end(`proxy error: ${error.message}`);
  });

  req.pipe(upstream);
};

const proxyToFlutter = (req, res) => {
  const upstream = http.request(
    {
      hostname: 'localhost',
      port: FLUTTER_PORT,
      path: req.url,
      method: req.method,
      headers: { ...req.headers, host: `localhost:${FLUTTER_PORT}` },
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode ?? 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    },
  );

  upstream.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'text/plain' });
    res.end(`flutter dev server not reachable: ${error.message}`);
  });

  req.pipe(upstream);
};

const server = http.createServer((req, res) => {
  if (isApi(req.url ?? '')) return proxyToApi(req, res);
  return proxyToFlutter(req, res);
});

server.listen(PROXY_PORT, () => {
  console.log(`[proxy] http://localhost:${PROXY_PORT}`);
  console.log(`[proxy] /api + /android  ->  ${TARGET.origin}`);
  console.log(`[proxy] everything else  ->  http://localhost:${FLUTTER_PORT}`);
  console.log(`[proxy] OPEN THIS -> http://localhost:${PROXY_PORT}`);
  console.log('[proxy] starting flutter...');

  const flutter = spawn(
    'flutter',
    [
      'run',
      '-d',
      'chrome',
      '--web-port',
      String(FLUTTER_PORT),
      '--dart-define=API_BASE_URL=',
    ],
    { stdio: 'inherit', shell: true },
  );

  flutter.on('exit', (code) => {
    server.close();
    process.exit(code ?? 0);
  });
});

const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const root = __dirname;
const dataDirectory = process.env.DATA_DIR || path.join(root, 'data');
const port = 8000;
const sessionLifetime = 8 * 60 * 60 * 1000;
const serviceLimit = 12 * 60 * 60 * 1000;
const cookieName = 'frota_session';
const loginAttempts = new Map();

fs.mkdirSync(dataDirectory, { recursive: true, mode: 0o700 });
const database = new DatabaseSync(path.join(dataDirectory, 'frota.sqlite'));
database.exec(`
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'member')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
  );
  CREATE TABLE IF NOT EXISTS app_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1
  );
  CREATE TABLE IF NOT EXISTS access_requests (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
  );
`);
const appStateColumns = database.prepare('PRAGMA table_info(app_state)').all().map(column => column.name);
if (!appStateColumns.includes('revision')) database.exec('ALTER TABLE app_state ADD COLUMN revision INTEGER NOT NULL DEFAULT 1');

const statements = {
  userCount: database.prepare('SELECT COUNT(*) AS count FROM users'),
  findUser: database.prepare('SELECT * FROM users WHERE username = ? COLLATE NOCASE'),
  findUserById: database.prepare('SELECT * FROM users WHERE id = ?'),
  listUsers: database.prepare('SELECT id, username, role, active, created_at AS createdAt FROM users ORDER BY created_at'),
  listAccessRequests: database.prepare('SELECT id, email, created_at AS createdAt FROM access_requests ORDER BY created_at'),
  findAccessRequest: database.prepare('SELECT * FROM access_requests WHERE id = ?'),
  insertAccessRequest: database.prepare('INSERT INTO access_requests (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)'),
  deleteAccessRequest: database.prepare('DELETE FROM access_requests WHERE id = ?'),
  activeAdmins: database.prepare("SELECT COUNT(*) AS count FROM users WHERE role = 'admin' AND active = 1"),
  insertUser: database.prepare('INSERT INTO users (id, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, 1, ?)'),
  createSession: database.prepare('INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)'),
  findSession: database.prepare('SELECT users.id, users.username, users.role FROM sessions JOIN users ON users.id = sessions.user_id WHERE sessions.token_hash = ? AND sessions.expires_at > ? AND users.active = 1'),
  deleteSession: database.prepare('DELETE FROM sessions WHERE token_hash = ?'),
  deleteUserSessions: database.prepare('DELETE FROM sessions WHERE user_id = ?'),
  updatePassword: database.prepare('UPDATE users SET password_hash = ? WHERE id = ?'),
  deactivateUser: database.prepare('UPDATE users SET active = 0 WHERE id = ?'),
  setUserActive: database.prepare('UPDATE users SET active = ? WHERE id = ?'),
  getState: database.prepare('SELECT value, revision FROM app_state WHERE id = 1'),
  setState: database.prepare('INSERT INTO app_state (id, value, updated_at, revision) VALUES (1, ?, ?, 1) ON CONFLICT(id) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at, revision = app_state.revision + 1 WHERE app_state.revision = ?')
};

function passwordHash(password) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(password, salt, 64);
  return `${salt.toString('hex')}:${hash.toString('hex')}`;
}

function passwordMatches(password, storedHash) {
  const [saltHex, hashHex] = String(storedHash).split(':');
  if (!saltHex || !hashHex) return false;
  const expected = Buffer.from(hashHex, 'hex');
  const actual = crypto.scryptSync(password, Buffer.from(saltHex, 'hex'), expected.length);
  return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
}

function validPassword(password) {
  return typeof password === 'string' && password.length >= 8 && password.length <= 128;
}

function validUsername(username) {
  return typeof username === 'string' && (/^[a-zA-Z0-9._-]{3,40}$/.test(username) || validEmail(username));
}

function validEmail(email) {
  return typeof email === 'string' && email.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

function safeUser(user) {
  return { id: user.id, username: user.username, role: user.role };
}

function cookies(request) {
  const header = request.headers.cookie || '';
  return Object.fromEntries(header.split(';').map(part => {
    const separator = part.indexOf('=');
    if (separator < 0) return ['', ''];
    return [part.slice(0, separator).trim(), part.slice(separator + 1).trim()];
  }).filter(([name]) => name));
}

function sessionToken(request) {
  return cookies(request)[cookieName] || '';
}

function hashToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

function sessionCookie(request, token, maxAge = Math.floor(sessionLifetime / 1000)) {
  const forwardedProtocol = String(request.headers['x-forwarded-proto'] || '').split(',')[0].trim();
  const secure = request.socket.encrypted || forwardedProtocol === 'https';
  const secureAttribute = secure ? '; Secure' : '';
  return `${cookieName}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${secureAttribute}`;
}

function currentUser(request) {
  const token = sessionToken(request);
  if (!token) return null;
  return statements.findSession.get(hashToken(token), Date.now()) || null;
}

function issueSession(response, request, user) {
  const token = crypto.randomBytes(32).toString('base64url');
  statements.createSession.run(hashToken(token), user.id, Date.now() + sessionLifetime);
  response.setHeader('Set-Cookie', sessionCookie(request, token));
}

function clearSession(response, request) {
  const token = sessionToken(request);
  if (token) statements.deleteSession.run(hashToken(token));
  response.setHeader('Set-Cookie', sessionCookie(request, '', 0));
}

function applySecurityHeaders(response) {
  response.setHeader('X-Content-Type-Options', 'nosniff');
  response.setHeader('X-Frame-Options', 'DENY');
  response.setHeader('Referrer-Policy', 'no-referrer');
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self' 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'");
}

function sendJson(response, status, body) {
  const payload = JSON.stringify(body);
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  response.end(payload);
}

function readJson(request, maximumBytes = 1024 * 1024) {
  return new Promise((resolve, reject) => {
    let body = '';
    let size = 0;
    request.setEncoding('utf8');
    request.on('data', chunk => {
      size += Buffer.byteLength(chunk);
      if (size > maximumBytes) {
        reject(Object.assign(new Error('Corpo da requisição muito grande.'), { status: 413 }));
        request.destroy();
        return;
      }
      body += chunk;
    });
    request.on('end', () => {
      try {
        resolve(JSON.parse(body || '{}'));
      } catch {
        reject(Object.assign(new Error('JSON inválido.'), { status: 400 }));
      }
    });
    request.on('error', reject);
  });
}

function sameOrigin(request) {
  const origin = request.headers.origin;
  if (!origin) return false;
  try {
    const allowedHosts = [request.headers.host, request.headers['x-forwarded-host']]
      .filter(Boolean)
      .flatMap(host => String(host).split(','))
      .map(host => host.trim().toLowerCase());
    return allowedHosts.includes(new URL(origin).host.toLowerCase());
  } catch {
    return false;
  }
}

function checkRateLimit(request) {
  const key = request.socket.remoteAddress || 'unknown';
  const now = Date.now();
  const recent = (loginAttempts.get(key) || []).filter(time => now - time < 15 * 60 * 1000);
  recent.push(now);
  loginAttempts.set(key, recent);
  return recent.length <= 10;
}

function validateFleetData(value) {
  return value && typeof value === 'object'
    && Array.isArray(value.vehicles)
    && Array.isArray(value.movements)
    && Array.isArray(value.odometerReadings)
    && value.vehicles.length <= 10000
    && value.movements.length <= 100000
    && value.odometerReadings.length <= 100000;
}

function readFleetData() {
  const row = statements.getState.get();
  if (!row) return { initialized: false, revision: 0, data: null };
  return { initialized: true, revision: row.revision, data: JSON.parse(row.value) };
}

function createFirstAdmin(username, password) {
  database.exec('BEGIN IMMEDIATE');
  try {
    if (statements.userCount.get().count !== 0) {
      database.exec('ROLLBACK');
      return null;
    }
    const user = { id: crypto.randomUUID(), username, role: 'admin' };
    statements.insertUser.run(user.id, username, passwordHash(password), user.role, new Date().toISOString());
    database.exec('COMMIT');
    return user;
  } catch (error) {
    database.exec('ROLLBACK');
    throw error;
  }
}

function staticFile(response, requestPath) {
  const files = {
    '/': ['index.html', 'text/html; charset=utf-8'],
    '/index.html': ['index.html', 'text/html; charset=utf-8'],
    '/litoral-med-20-anos.png': ['litoral-med-20-anos.png', 'image/png']
  };
  const entry = files[requestPath];
  if (!entry) return false;
  const [fileName, contentType] = entry;
  const contents = fs.readFileSync(path.join(root, fileName));
  response.writeHead(200, { 'Content-Type': contentType, 'Content-Length': contents.length });
  response.end(contents);
  return true;
}

async function handleRequest(request, response) {
  applySecurityHeaders(response);
  const requestUrl = new URL(request.url, 'http://localhost');
  const requestPath = requestUrl.pathname;
  const method = request.method;

  if (method === 'GET' && staticFile(response, requestPath)) return;

  if (method === 'GET' && requestPath === '/api/session') {
    const user = currentUser(request);
    return sendJson(response, 200, { setupRequired: statements.userCount.get().count === 0, authenticated: Boolean(user), user: user ? safeUser(user) : null });
  }

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && requestPath.startsWith('/api/') && !sameOrigin(request)) {
    return sendJson(response, 403, { error: 'Origem da solicitação inválida.' });
  }

  if (method === 'POST' && requestPath === '/api/access-requests') {
    if (!checkRateLimit(request)) return sendJson(response, 429, { error: 'Muitas tentativas. Aguarde 15 minutos.' });
    const body = await readJson(request);
    const email = typeof body.email === 'string' ? body.email.trim().toLowerCase() : '';
    if (!validEmail(email)) return sendJson(response, 400, { error: 'Informe um e-mail válido.' });
    if (!validPassword(body.password)) return sendJson(response, 400, { error: 'A senha deve ter entre 8 e 128 caracteres.' });
    const existingUser = statements.findUser.get(email);
    if (!existingUser) {
      try {
        statements.insertAccessRequest.run(crypto.randomUUID(), email, passwordHash(body.password), new Date().toISOString());
      } catch (error) {
        if (!String(error.code).startsWith('SQLITE_CONSTRAINT')) throw error;
      }
    }
    return sendJson(response, 202, { ok: true });
  }

  if (method === 'POST' && requestPath === '/api/setup') {
    if (!checkRateLimit(request)) return sendJson(response, 429, { error: 'Muitas tentativas. Aguarde 15 minutos.' });
    const body = await readJson(request);
    if (!validUsername(body.username)) return sendJson(response, 400, { error: 'Use um usuário de 3 a 40 caracteres: letras, números, ponto, hífen ou sublinhado.' });
    if (!validPassword(body.password)) return sendJson(response, 400, { error: 'A senha deve ter entre 8 e 128 caracteres.' });
    const user = createFirstAdmin(body.username, body.password);
    if (!user) return sendJson(response, 409, { error: 'A configuração inicial já foi concluída.' });
    loginAttempts.delete(request.socket.remoteAddress || 'unknown');
    issueSession(response, request, user);
    return sendJson(response, 201, { user });
  }

  if (method === 'POST' && requestPath === '/api/login') {
    if (!checkRateLimit(request)) return sendJson(response, 429, { error: 'Muitas tentativas. Aguarde 15 minutos.' });
    const body = await readJson(request);
    const user = typeof body.username === 'string' ? statements.findUser.get(body.username.trim()) : null;
    const matches = passwordMatches(typeof body.password === 'string' ? body.password : '', user?.password_hash || '00:00');
    if (!user || !user.active || !matches) return sendJson(response, 401, { error: 'Usuário ou senha inválidos.' });
    loginAttempts.delete(request.socket.remoteAddress || 'unknown');
    issueSession(response, request, user);
    return sendJson(response, 200, { user: safeUser(user) });
  }

  if (method === 'POST' && requestPath === '/api/logout') {
    clearSession(response, request);
    return sendJson(response, 200, { ok: true });
  }

  const user = currentUser(request);
  if (!user) return sendJson(response, 401, { error: 'Sessão encerrada. Entre novamente.' });

  if (method === 'GET' && requestPath === '/api/data') return sendJson(response, 200, readFleetData());

  if (method === 'PUT' && requestPath === '/api/data') {
    const body = await readJson(request);
    if (!validateFleetData(body)) return sendJson(response, 400, { error: 'Formato dos dados da frota inválido.' });
    const currentRevision = statements.getState.get()?.revision || 0;
    if (!Number.isSafeInteger(body.revision) || body.revision !== currentRevision) return sendJson(response, 409, { error: 'Outro usuário atualizou a frota. Recarregue a página antes de continuar.' });
    const { revision, ...fleetData } = body;
    const updateResult = statements.setState.run(JSON.stringify(fleetData), new Date().toISOString(), revision);
    if (updateResult.changes !== 1) return sendJson(response, 409, { error: 'Outro usuário atualizou a frota. Recarregue a página antes de continuar.' });
    const saved = statements.getState.get();
    if (saved.revision !== currentRevision + 1) return sendJson(response, 409, { error: 'Outro usuário atualizou a frota. Recarregue a página antes de continuar.' });
    return sendJson(response, 200, { ok: true, revision: saved.revision });
  }

  if (requestPath === '/api/users') {
    if (user.role !== 'admin') return sendJson(response, 403, { error: 'Apenas administradores podem gerenciar usuários.' });
    if (method === 'GET') return sendJson(response, 200, { users: statements.listUsers.all() });
    if (method === 'POST') {
      const body = await readJson(request);
      if (!validUsername(body.username)) return sendJson(response, 400, { error: 'Use um usuário de 3 a 40 caracteres: letras, números, ponto, hífen ou sublinhado.' });
      if (!validPassword(body.password)) return sendJson(response, 400, { error: 'A senha deve ter entre 8 e 128 caracteres.' });
      if (!['admin', 'member'].includes(body.role)) return sendJson(response, 400, { error: 'Selecione um perfil de acesso válido.' });
      const newUser = { id: crypto.randomUUID(), username: body.username.trim(), role: body.role };
      try {
        statements.insertUser.run(newUser.id, newUser.username, passwordHash(body.password), newUser.role, new Date().toISOString());
      } catch (error) {
        if (String(error.code).startsWith('SQLITE_CONSTRAINT')) return sendJson(response, 409, { error: 'Esse usuário já existe.' });
        throw error;
      }
      return sendJson(response, 201, { user: newUser });
    }
  }

  if (requestPath === '/api/access-requests') {
    if (user.role !== 'admin') return sendJson(response, 403, { error: 'Apenas administradores podem revisar solicitações.' });
    if (method === 'GET') return sendJson(response, 200, { requests: statements.listAccessRequests.all() });
  }

  const accessRequestAction = requestPath.match(/^\/api\/access-requests\/([\w-]+)\/(approve|deny)$/);
  if (accessRequestAction) {
    if (user.role !== 'admin') return sendJson(response, 403, { error: 'Apenas administradores podem revisar solicitações.' });
    const [, requestId, action] = accessRequestAction;
    const accessRequest = statements.findAccessRequest.get(requestId);
    if (!accessRequest) return sendJson(response, 404, { error: 'Solicitação não encontrada.' });
    if (method === 'POST' && action === 'approve') {
      database.exec('BEGIN IMMEDIATE');
      try {
        const newUser = { id: crypto.randomUUID(), username: accessRequest.email, role: 'member' };
        statements.insertUser.run(newUser.id, newUser.username, accessRequest.password_hash, newUser.role, new Date().toISOString());
        statements.deleteAccessRequest.run(requestId);
        database.exec('COMMIT');
        return sendJson(response, 201, { user: newUser });
      } catch (error) {
        database.exec('ROLLBACK');
        if (String(error.code).startsWith('SQLITE_CONSTRAINT')) return sendJson(response, 409, { error: 'Este e-mail já possui uma conta.' });
        throw error;
      }
    }
    if (method === 'DELETE' && action === 'deny') {
      statements.deleteAccessRequest.run(requestId);
      return sendJson(response, 200, { ok: true });
    }
  }

  const userAction = requestPath.match(/^\/api\/users\/([\w-]+)\/(password)$/);
  if (userAction && method === 'PUT') {
    if (user.role !== 'admin') return sendJson(response, 403, { error: 'Apenas administradores podem redefinir senhas.' });
    const target = statements.findUserById.get(userAction[1]);
    if (!target) return sendJson(response, 404, { error: 'Usuário não encontrado.' });
    const body = await readJson(request);
    if (!validPassword(body.password)) return sendJson(response, 400, { error: 'A senha deve ter entre 8 e 128 caracteres.' });
    statements.updatePassword.run(passwordHash(body.password), target.id);
    statements.deleteUserSessions.run(target.id);
    return sendJson(response, 200, { ok: true });
  }

  const userActive = requestPath.match(/^\/api\/users\/([\w-]+)\/active$/);
  if (userActive && method === 'PATCH') {
    if (user.role !== 'admin') return sendJson(response, 403, { error: 'Apenas administradores podem alterar o acesso.' });
    const target = statements.findUserById.get(userActive[1]);
    if (!target) return sendJson(response, 404, { error: 'Usuário não encontrado.' });
    const body = await readJson(request);
    if (typeof body.active !== 'boolean') return sendJson(response, 400, { error: 'Informe se a conta deve ficar ativa.' });
    if (!body.active && target.id === user.id) return sendJson(response, 400, { error: 'Você não pode desativar sua própria conta.' });
    if (!body.active && target.active && target.role === 'admin' && statements.activeAdmins.get().count <= 1) return sendJson(response, 400, { error: 'Mantenha ao menos um administrador ativo.' });
    statements.setUserActive.run(body.active ? 1 : 0, target.id);
    if (!body.active) statements.deleteUserSessions.run(target.id);
    return sendJson(response, 200, { ok: true });
  }

  const userDelete = requestPath.match(/^\/api\/users\/([\w-]+)$/);
  if (userDelete && method === 'DELETE') {
    if (user.role !== 'admin') return sendJson(response, 403, { error: 'Apenas administradores podem desativar usuários.' });
    const target = statements.findUserById.get(userDelete[1]);
    if (!target || !target.active) return sendJson(response, 404, { error: 'Usuário ativo não encontrado.' });
    if (target.id === user.id) return sendJson(response, 400, { error: 'Você não pode desativar sua própria conta.' });
    if (target.role === 'admin' && statements.activeAdmins.get().count <= 1) return sendJson(response, 400, { error: 'Mantenha ao menos um administrador ativo.' });
    statements.deactivateUser.run(target.id);
    statements.deleteUserSessions.run(target.id);
    return sendJson(response, 200, { ok: true });
  }

  return sendJson(response, 404, { error: 'Rota não encontrada.' });
}

function startServer(listenPort) {
  const server = http.createServer((request, response) => {
    handleRequest(request, response).catch(error => {
      if (response.headersSent || response.destroyed) return;
      const status = Number(error.status) || 500;
      if (status === 500) console.error('Falha na requisição:', error);
      sendJson(response, status, { error: status === 500 ? 'Erro interno do servidor.' : error.message });
    });
  });

  server.on('error', error => {
    if (error.code === 'EADDRINUSE') {
      console.error(`A porta ${listenPort} já está em uso. O servidor não será iniciado em outra porta.`);
      process.exitCode = 1;
      return;
    }

    throw error;
  });

  server.listen(listenPort, '0.0.0.0', () => {
    console.log(`Frota Litoral Med disponível em http://localhost:${listenPort}`);
    console.log(`Banco compartilhado: ${path.join(dataDirectory, 'frota.sqlite')}`);
    console.log('O servidor será encerrado automaticamente após 12 horas de serviço.');
  });

  setTimeout(() => {
    console.log('Limite de 12 horas de serviço atingido. Encerrando o servidor.');
    server.close(() => {
      database.close();
      process.exit(0);
    });
    server.closeAllConnections();
  }, serviceLimit);
}

startServer(port);


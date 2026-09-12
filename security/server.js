require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const jwt = require('jsonwebtoken');
const multer = require('multer');
const rateLimit = require('express-rate-limit');
const { body, validationResult } = require('express-validator');
const requestLogger = require('./middleware/requestLogger');
const { hasPermission, canAccessSubsidiary } = require('./config/roles');

const app = express();
const PORT = Number(process.env.GATEWAY_PORT || 3000);
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const JWT_SECRET = process.env.JWT_SECRET || 'koha-cil-dev-jwt-secret-change-in-production';
const INTERNAL_SECRET = process.env.INTERNAL_SECRET || 'koha-cil-internal-shared-secret';
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 25 * 1024 * 1024 } });

app.use(cors({ origin: process.env.FRONTEND_ORIGIN || 'http://localhost:5173', methods: ['GET', 'POST'], allowedHeaders: ['Content-Type', 'Authorization'] }));
app.use(express.json({ limit: '1mb' }));
app.use(requestLogger);
app.use('/api/auth', rateLimit({ windowMs: 15 * 60 * 1000, max: 20, standardHeaders: true, legacyHeaders: false }));

function fail(res, status, message) { return res.status(status).json({ success: false, message }); }
function authenticate(req, res, next) {
  const token = req.headers.authorization?.replace(/^Bearer\s+/i, '');
  if (!token) return fail(res, 401, 'Authentication is required.');
  try { req.user = jwt.verify(token, JWT_SECRET); return next(); }
  catch (_) { return fail(res, 401, 'Your session is invalid or has expired.'); }
}
function permit(permission) { return (req, res, next) => hasPermission(req.user.role, permission) ? next() : fail(res, 403, 'You do not have permission for this action.'); }
function backendHeaders(req) { return { 'X-Internal-Auth': INTERNAL_SECRET, 'X-Username': req.user.username, 'X-Role': req.user.role, 'X-Subsidiary': req.user.subsidiary || '', 'X-Request-Id': req.requestId }; }
async function proxy(req, res, method, path, config = {}) {
  try {
    const response = await axios({ method, url: `${BACKEND_URL}${path}`, headers: backendHeaders(req), validateStatus: () => true, ...config });
    return res.status(response.status).json(response.data);
  } catch (_) { return fail(res, 503, 'The intelligence service is currently unavailable. Please try again shortly.'); }
}

app.get('/health', async (_req, res) => {
  try { const r = await axios.get(`${BACKEND_URL}/health`, { timeout: 3000 }); res.json({ status: 'ok', service: 'security', details: { backend: r.data.status } }); }
  catch (_) { res.status(503).json({ status: 'degraded', service: 'security', details: { backend: 'unavailable' } }); }
});

app.post('/api/auth/login', [body('username').trim().isLength({ min: 1, max: 64 }), body('password').isLength({ min: 1, max: 128 })], async (req, res) => {
  if (!validationResult(req).isEmpty()) return fail(res, 400, 'Username and password are required.');
  try {
    const r = await axios.post(`${BACKEND_URL}/internal/auth/verify`, req.body, { headers: { 'X-Internal-Auth': INTERNAL_SECRET }, validateStatus: () => true });
    if (r.status !== 200 || !r.data?.user) return fail(res, 401, 'Invalid username or password.');
    const user = r.data.user;
    const session = { username: user.username, role: user.role, subsidiary: user.subsidiary || null };
    const token = jwt.sign(session, JWT_SECRET, { expiresIn: process.env.JWT_EXPIRES_IN || '8h' });
    req.user = session;
    return res.json({ success: true, token, user: session, expiresIn: process.env.JWT_EXPIRES_IN || '8h' });
  } catch (_) { return fail(res, 503, 'Authentication service is currently unavailable.'); }
});

app.get('/api/dashboard/stats', authenticate, permit('VIEW_DASHBOARD'), (req, res) => proxy(req, res, 'get', '/internal/dashboard/stats'));
app.post('/api/query', authenticate, permit('QUERY_OWN'), [body('query').trim().isLength({ min: 1, max: 2000 })], (req, res) => {
  if (!validationResult(req).isEmpty()) return fail(res, 400, 'Please enter a valid question.');
  return proxy(req, res, 'post', '/internal/query', { data: { query: req.body.query } });
});
app.get('/api/ingestion/jobs', authenticate, permit('INGEST'), (req, res) => proxy(req, res, 'get', '/internal/ingestion/jobs'));
app.post('/api/ingest', authenticate, permit('INGEST'), upload.single('file'), async (req, res) => {
  if (!req.file) return fail(res, 400, 'Select a document to ingest.');
  try {
    const form = new FormData();
    form.append('file', new Blob([req.file.buffer], { type: req.file.mimetype || 'application/octet-stream' }), req.file.originalname);
    return proxy(req, res, 'post', '/internal/ingest', { data: form, headers: { ...backendHeaders(req), ...Object.fromEntries(form.headers || []) } });
  } catch (_) { return fail(res, 503, 'The document service is currently unavailable.'); }
});
app.get('/api/conflicts', authenticate, permit('VIEW_CONFLICTS'), (req, res) => proxy(req, res, 'get', '/internal/conflicts', { params: { status: req.query.status } }));
app.post('/api/conflicts/:id/review', authenticate, permit('REVIEW_CONFLICTS'), [body('action').isIn(['APPROVED', 'REJECTED'])], (req, res) => {
  if (!validationResult(req).isEmpty()) return fail(res, 400, 'A valid review action is required.');
  return proxy(req, res, 'post', `/internal/conflicts/${encodeURIComponent(req.params.id)}/review`, { data: { action: req.body.action, reviewer: req.user.username } });
});
app.get('/api/audit', authenticate, permit('VIEW_AUDIT'), (req, res) => proxy(req, res, 'get', '/internal/audit', { params: { limit: req.query.limit, action: req.query.action, username: req.query.username } }));

app.use((_req, res) => fail(res, 404, 'Endpoint not found.'));
app.use((err, _req, res, _next) => {
  if (err instanceof multer.MulterError && err.code === 'LIMIT_FILE_SIZE') return fail(res, 413, 'The selected document exceeds the 25 MB upload limit.');
  console.error('Gateway error:', err.message);
  return fail(res, 500, 'An unexpected gateway error occurred.');
});
app.listen(PORT, () => console.log(`KOHA-CIL Security Gateway listening on port ${PORT}`));

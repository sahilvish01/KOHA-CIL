/**
 * KOHA-CIL Security Gateway — Request Logger Middleware
 * Generates a unique request ID for every request and logs it.
 */
const { v4: uuidv4 } = require('uuid');

function requestLogger(req, res, next) {
  const requestId = uuidv4();
  req.requestId = requestId;

  const start = Date.now();
  const timestamp = new Date().toISOString();

  res.on('finish', () => {
    const duration = Date.now() - start;
    const level = res.statusCode >= 500 ? 'ERROR' :
                  res.statusCode >= 400 ? 'WARN'  : 'INFO';
    console.log(
      `[${level}] ${timestamp} | ${requestId} | ${req.method} ${req.originalUrl} | ` +
      `${res.statusCode} | ${duration}ms | ${req.user?.username || 'anonymous'}`
    );
  });

  next();
}

module.exports = requestLogger;

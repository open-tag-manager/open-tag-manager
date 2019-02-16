'use strict'
module.exports = {
  NODE_ENV: '"production"',
  API_BASE_URL: `"${process.env.API_BASE_URL || 'http://localhost:8000'}"`,
  BASE_PATH: `"${process.env.BASE_PATH || '/'}"`,
  COGNITO_IDENTITY_POOL_ID: `"${process.env.COGNITO_IDENTITY_POOL_ID}"`,
  COGNITO_REGION: `"${process.env.COGNITO_REGION}"`,
  COGNITO_IDENTITY_POOL_REGION: `"${process.env.COGNITO_IDENTITY_POOL_REGION}"`,
  COGNITO_USER_POOL_ID: `"${process.env.COGNITO_USER_POOL_ID}"`,
  COGNITO_USER_POOL_WEB_CLIENT_ID: `"${process.env.COGNITO_USER_POOL_WEB_CLIENT_ID}"`,
  COGNITO_COOKIE_STORAGE_DOMAIN: `"${process.env.COGNITO_COOKIE_STORAGE_DOMAIN}"`,
  COGNITO_COOKIE_SECURE: `"${process.env.COGNITO_COOKIE_SECURE}"`
}

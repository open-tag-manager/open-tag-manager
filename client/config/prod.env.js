'use strict'

module.exports = {
  NODE_ENV: '"production"',
  API_BASE_URL: `"${process.env.API_BASE_URL || 'http://localhost:8000'}"`,
  BASE_PATH: `"${process.env.BASE_PATH || '/'}"`
}

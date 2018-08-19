switch (process.env.NODE_ENV) {
  case 'prod':
  case 'production':
    module.exports = require('./config/webpack.prod');
    break;
  case 'test':
  case 'testing':
    module.exports = require('./config/webpack.test');
    break;
  case 'stg':
  case 'staging':
    module.exports = require('./config/webpack.stg');
    break;
  case 'dev':
  case 'development':
  default:
    module.exports = require('./config/webpack.dev');
}

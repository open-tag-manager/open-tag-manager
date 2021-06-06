const path = require('path');
const webpack = require('webpack');

module.exports = {
  entry: './src/main.js',
  output: {
    path: path.join(__dirname, '..', 'dist'),
    filename: 'otm.js'
  },
  module: {
    loaders: [
      {test: /\.js$/, loader: 'babel-loader', exclude: /node_modules/},
    ]
  },
  devtool: 'eval-source-map'
};

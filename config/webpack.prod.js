const path = require('path');
const webpackMerge = require('webpack-merge');
const commonConfig = require('./webpack.common.js');
const fs = require('fs');

// webpack plugins
const webpack = require('webpack');
const UglifyJsPlugin = require('webpack/lib/optimize/UglifyJsPlugin');

module.exports = webpackMerge(commonConfig, {
  devtool: 'source-map',
  plugins: [
    new UglifyJsPlugin()
  ]
});

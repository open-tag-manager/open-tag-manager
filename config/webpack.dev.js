const webpackMerge = require('webpack-merge');
const webpack = require('webpack');
const commonConfig = require('./webpack.common.js');
const fs = require('fs');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = webpackMerge(commonConfig, {
  plugins: [
    new HtmlWebpackPlugin({
      template: 'src/sample.html',
      filename: 'sample.html',
      inject: 'head'
    })
  ]
});

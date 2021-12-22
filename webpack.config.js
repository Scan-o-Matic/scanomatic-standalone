const path = require('path');
const webpack = require('webpack');

module.exports = {
  entry: {
    ccc: [path.join(__dirname, 'scanomatic/ui_server_data/js/ccc/index.jsx')],
    som: [path.join(__dirname, './scanomatic/ui_server_data/js/som/index.js')],
  },
  output: {
    path: path.join(__dirname, 'scanomatic/ui_server_data/js'),
    filename: '[name].js',
    library: ['[name]'],
    libraryTarget: 'umd',
    publicPath: '/js/som',
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
        },
      },
      {
        test: /\.png$/,
        use: {
          loader: 'file-loader',
        },
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  resolve: {
    extensions: ['.js', '.json', '.jsx'],
  },
  plugins: [
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
    }),
  ],
};

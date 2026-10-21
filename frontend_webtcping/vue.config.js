const path = require("path");

// 在vue-config.js 中加入
module.exports = {

  transpileDependencies: ["vuetify"],
  devServer: {
    host: "0.0.0.0",
    port: 8080,
    disableHostCheck: true,
  },
  // 配置webpack

  configureWebpack: config => {

    // webpack 4 ignores package "exports"; point the OpenTelemetry subpath at its ES build
    config.resolve = config.resolve || {};
    config.resolve.alias = Object.assign({}, config.resolve.alias, {
      "@opentelemetry/otlp-exporter-base/browser-http": path.resolve(
        __dirname,
        "node_modules/@opentelemetry/otlp-exporter-base/build/esm/index-browser-http.js"
      )
    });

    // 开启分离js
    config.optimization = {
      runtimeChunk: 'single',
      splitChunks: {
        chunks: 'all',
        maxInitialRequests: Infinity,
        minSize: 20000,
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name(module) {
              // get the name. E.g. node_modules/packageName/not/this/part.js
              // or node_modules/packageName
              const packageName = module.context.match(/[\\/]node_modules[\\/](.*?)([\\/]|$)/)[1]
              // npm package names are URL-safe, but some servers don't like @ symbols
              return `npm.${packageName.replace('@', '')}`
            }
          }
        }
      }
    };

  }
}
// 至此，你会发现原先的vender文件没有了，同时多了好几个依赖的js文件


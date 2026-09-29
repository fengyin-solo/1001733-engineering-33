import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 主机/端口/后端地址都从环境变量读取，默认值与根目录 .env.example 保持一致。
// 换端口调试、容器部署或做启动探针时只改环境变量，不动这份配置。
const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000'
const devHost = process.env.VITE_DEV_HOST ?? '127.0.0.1'
const devPort = Number(process.env.VITE_DEV_PORT ?? 5173)

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: devHost,
    port: devPort,
    // 关掉自动打开页面：起服务时只打印地址，不拉起浏览器；
    // 端口被占用时直接失败而不是悄悄换端口，保证部署产出可预期
    open: false,
    strictPort: true,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})

import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端地址默认取配置基线里的端口，起服务时可以用 VITE_PROXY_TARGET 覆盖，
// 这样换端口调试或做启动探针时前端不用改代码。
const proxyTarget = process.env.VITE_PROXY_TARGET ?? `http://127.0.0.1:${process.env.APP_PORT ?? '8000'}`
// 监听地址与端口同样走环境变量：本机默认 127.0.0.1:5173，容器里覆盖为 0.0.0.0。
const host = process.env.VITE_HOST ?? '127.0.0.1'
const port = Number(process.env.FRONTEND_PORT ?? '5173')

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host,
    port,
    // 关掉自动打开页面：起服务时只打印地址，不拉起浏览器
    open: false,
    // 端口被占用时直接失败，避免悄悄换端口导致本地与部署不是同一个结果
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

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 后端地址：默认本地 FastAPI；可用环境变量 VITE_API_TARGET 覆盖
// （例如指向已部署的服务器做联调）。生产是同源（前端用相对路径），不走代理。
// 用 127.0.0.1 而不是 localhost：避免 Windows 下 localhost 被解析成 IPv6(::1)，
// 而 uvicorn 默认监听 IPv4，导致代理连不上。
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/predict': { target: apiTarget, changeOrigin: true },
      '/translate': { target: apiTarget, changeOrigin: true },
    },
  },
})

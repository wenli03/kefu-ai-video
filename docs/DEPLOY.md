# AI视频客服 - 免费部署到外网

## 一键部署步骤

### 1. 推送到 GitHub
```bash
# 先在 github.com 创建新仓库 (如: kefu-ai-video)
git remote add origin https://github.com/你的用户名/kefu-ai-video.git
git branch -M main
git push -u origin main
```

### 2. 部署到 Render.com (推荐，免费，最简单)
1. 打开 https://render.com
2. 注册账号 (用GitHub登录)
3. 点击 `New +` → `Web Service`
4. 选择刚刚推送的仓库
5. 配置:
   - Name: `ai-video-cs`
   - Environment: `Node`
   - Build Command: (留空)
   - Start Command: `node deploy-server.js`
   - Free Instance Type: 选择
6. 点击 `Deploy Web Service`
7. 等待部署完成 (约2分钟)
8. 获取URL: `https://ai-video-cs.onrender.com`

### 3. 写进简历
```
项目地址: https://ai-video-cs.onrender.com
项目描述: AI视频客服系统 - 基于WebSocket的实时对话数字人
```

## 备选方案

### Fly.io (免费, 不自动休眠, 需信用卡验证)
```bash
# 安装 flyctl
powershell -c "iwr https://fly.io/install.ps1 -useb | iex"
fly auth login
fly launch --name ai-video-cs
fly deploy
# URL: https://ai-video-cs.fly.dev
```

### Koyeb (免费, 不休眠)
1. https://koyeb.com 注册
2. 创建 App → GitHub 仓库
3. 选择 `deploy-server.js` 作为入口
4. URL: `https://ai-video-cs.koyeb.app`

## 端口说明
- 服务自动使用 `$PORT` 环境变量（Render 自动分配）
- 健康检查: `GET /api/cc/admin/stats`

## 文件说明
- `deploy-server.js` - 统一服务器（前端静态文件 + CC Mock + WebSocket）
- `web/public/audio/*.mp3` - 预生成TTS音频（无需Python依赖）
- `web/public/avatar-videos/*.webm` - 数字人视频
- `web/dist/` - Vite构建的前端文件

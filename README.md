# 已失效

# AI 聊天 API

yeschat.ai 服务逆向接口，接口适配openai chat api。它使用 FastAPI 构建，可以作为独立应用程序、Docker 容器或在 Vercel 上部署。

## 功能特点

- 兼容 OpenAI API 格式的聊天完成 API 端点
- 支持流式和非流式响应选项
- 支持跨源资源共享（CORS）
- 提供日志记录，便于调试和监控
- 支持 `gpt-4o` 模型

## 设置和安装

1. 克隆仓库

2. 安装依赖：

   ```sh
   pip install -r requirements.txt
   ```

3. 设置环境变量：
   - 在根目录创建 `.env` 文件
   - 添加你的 APP_SECRET：`APP_SECRET=你的密钥`
4. 运行 API：

   ```sh
   python api/main.py
   ```

## 构建

你可以使用 `build.py` 脚本为你的平台构建独立可执行文件：

  ```sh
  python build.py
  ```

这将在 `dist` 目录中创建一个名为 `yeschat2api` 的可执行文件。

## Docker

构建和运行 Docker 容器：

  ```sh
  docker build -t yeschat2api .
  docker run -d --name yeschat2api --restart always -p 8001:8001 -e APP_SECRET=你的密钥 yeschat2api
  ```

## 部署

本项目包含一个 `vercel.json` 配置文件，便于在 Vercel 上部署。确保在 Vercel 项目设置中将 APP_SECRET 设置为环境变量。

## 快速部署

[![使用 Vercel 部署](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/snailyp/yeschat-reverse)

## 使用方法

向 `/v1/chat/completions` 发送 POST 请求，请求体中包含聊天消息和模型规格的 JSON。在 Authorization 头中包含你的 `Bearer APP_SECRET`。
示例：

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "user", "content": "你好，你好吗？"}
  ],
  "stream": false
}
```

## 支持的模型

目前，API 支持以下模型：

- gpt-4o

## 安全性

此 API 使用 APP_SECRET 进行身份验证。确保保管好你的 APP_SECRET，不要在客户端代码中暴露它。

## 免责声明

本项目仅用于教育目的。它不隶属于 yeschat.ai 或其任何附属机构或子公司，也未经其授权、维护、赞助或认可。本软件不应用于任何非法活动或违反 yeschat.ai 或任何其他服务提供商的服务条款。
本项目的作者和贡献者不对本软件的任何滥用或违反任何第三方服务条款的行为负责。用户应自行负责确保其使用本软件符合所有适用法律和服务条款。
使用本软件风险自负。作者和贡献者不提供任何形式的明示或暗示的保证或担保。

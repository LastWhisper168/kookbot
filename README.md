# KOOK Bot - 多Agent智能体聊天机器人

一个基于[khl.py](https://github.com/TWT233/khl.py)的KOOK平台智能聊天机器人，采用多Agent架构设计，支持知识检索、情感分析和上下文对话。

## 项目简介

本项目是一个运行在KOOK（开黑啦）平台上的AI聊天机器人，具有以下特点：

- **多Agent架构**：使用多个智能体协同工作，包括对话生成、知识检索、情感分析等
- **上下文记忆**：能够记住与用户的对话历史，提供连贯的交流体验
- **知识库存储**：支持存储和检索用户信息和知识点
- **情感分析**：能够识别和响应用户的情感状态
- **API集成**：内置通用API客户端，支持与外部服务交互

## 安装步骤

### 环境要求

- Python 3.6+
- 依赖包：aiohttp, pycryptodomex, apscheduler, rich, python-dotenv

### 安装依赖

```bash
# 克隆仓库
git clone https://github.com/LastWhisper168/kookbot.git
cd kookbot

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

1. 复制环境变量示例文件为实际配置文件：

```bash
cp .env.example .env
```

2. 编辑`.env`文件，填入实际的配置值：

```
# KOOK Bot 基本配置
KOOK_WS_TOKEN=your_kook_bot_token_here         # KOOK Bot 的 WebSocket Token
KOOK_BOT_ID=your_bot_id_here                   # 本 Bot 的 ID  

# 主模型（检索用）
SF_APIKEY=your_primary_api_key_here            # 主模型的 API 密钥
SF_APIURL=https://api.example.com/v1           # 主模型的 API 地址
SF_MODEL=model-name-here                       # 主模型名称
```

## 使用示例

### 启动机器人

```bash
# 在Windows上
start.bat

# 在Linux/macOS上
python bot.py
```

### 基本交互

在KOOK频道中：
- 使用"麦麦"唤醒机器人（例如："麦麦，你好！"）
- 在私聊中无需唤醒词，直接发送消息即可
- 使用👍或👎对机器人回复进行反馈
- 使用"记住xxx"让机器人记住特定信息

### 命令列表

| 命令 | 描述 |
|------|------|
| `/reset` | 重置与用户的对话历史 |
| `/ping` | 检查机器人运行状态和运行时间 |
| `/api_test [用户ID]` | 测试API调用功能 |

## 项目结构

```
kook-bot/
├── bot.py                 # 主程序入口
├── api_client.py          # API客户端模块
├── .env.example           # 环境变量示例
├── data/                  # 数据存储目录
│   ├── users.json         # 用户数据
│   └── knowledge.json     # 知识库数据
└── khl/                   # khl.py SDK
```

## 核心功能

### 多Agent系统

机器人使用多个智能体协同工作：

- **DialogueAgent**: 负责生成对话回复
- **RetrievalAgent**: 负责知识检索
- **EmotionAgent**: 负责情感分析
- **FeedbackAgent**: 处理用户反馈

### 弹性并发控制

使用`AdaptiveSemaphore`类实现自适应并发控制，根据响应延迟自动调整并发限制。

### API客户端

内置通用API客户端，支持重试机制、异常处理和日志记录。

## 贡献指南

欢迎贡献代码或提出建议！请遵循以下步骤：

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个Pull Request

## 许可证

本项目采用MIT许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

```
MIT License

Copyright (c) 2022 TWT233

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

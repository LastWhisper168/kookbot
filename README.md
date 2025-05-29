# KOOK Bot - 多Agent智能体聊天机器人

一个基于[khl.py](https://github.com/TWT233/khl.py)的KOOK平台智能聊天机器人，采用多Agent架构设计，支持智能对话、辱骂检测反击、连续对话和情感分析等功能。

![Version](https://img.shields.io/badge/version-v1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

## 🌟 主要特性

- **🤖 多Agent智能体架构** - 思考链、情感分析、对话生成、人格系统等多个Agent协同工作
- **🛡️ 智能辱骂检测与反击** - 自动检测辱骂并生成个性化反击回复
- **💬 连续对话支持** - 被@或使用唤醒词后180秒内可连续对话，无需重复触发
- **🧠 上下文记忆** - 记住对话历史，提供连贯的交流体验
- **😊 情感分析** - 智能识别用户情感状态并做出相应回应
- **📚 知识库管理** - 支持动态学习和存储用户信息
- **🔧 环境变量配置** - 第三方API客户端支持从.env文件读取配置
- **📊 MongoDB集成** - 可选的数据库支持，用于用户数据持久化


## 交流频道
https://kook.vip/izhvYt


## 📋 核心功能

### 🤖 智能对话系统

**多种触发方式**：
- **群聊触发**：@机器人 或 使用唤醒词"麦麦"
- **私聊触发**：直接发送消息，无需唤醒词
- **连续对话**：触发后180秒内可连续对话，无需重复@或唤醒

**智能Agent协作**：
- **ThinkingAgent** - 思考链推理，分析用户意图
- **EmotionAgent** - 情感分析，识别用户情感状态  
- **DialogueAgent** - 对话生成，提供自然流畅的回复
- **PersonalityAgent** - 人格系统，保持一致的对话风格

### 🛡️ 辱骂检测与反击

**智能检测**：
- 150+ 辱骂关键词库，包括家人相关、极端辱骂等
- 正则表达式模式匹配，防止变形绕过
- 连续脏话组合检测

**个性化反击**：
- 25+ 种不同风格反击模板（直接硬刚、讽刺挖苦、霸气反击等）
- LLM生成孙吧老哥风格反击回复
- 智能选择最适合的反击方式

### 📚 知识管理系统

**动态学习**：
- "记住xxx" - 让机器人记住特定信息
- 自动提取和存储关键信息
- 上下文关联知识检索

**数据持久化**：
- JSON文件本地存储
- 可选MongoDB数据库支持
- 用户数据和对话历史管理

### 🔧 配置化API客户端

**环境变量驱动**：
- 从.env文件读取第三方API配置
- 支持多种LLM模型切换（GPT、DeepSeek等）
- 灵活的API超时和重试设置

## 🚀 快速开始

### 环境要求

- **Python 3.6+**
- **依赖包**：aiohttp, pycryptodomex, apscheduler, rich, python-dotenv, numpy

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/LastWhisper168/kookbot.git
cd kookbot

# 2. 创建虚拟环境（推荐）
python -m venv kook_bot_env
source kook_bot_env/bin/activate  # Linux/macOS
# 或 kook_bot_env\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
# 或手动安装核心依赖
pip install aiohttp pycryptodomex apscheduler rich python-dotenv numpy
```

### 配置环境变量

1. 复制环境变量示例文件为实际配置文件：

```bash
cp .env.example .env
```

### 配置环境变量

1. **复制环境变量示例文件**：

```bash
cp .env.example .env
```

2. **编辑 `.env` 文件，填入实际配置**：

```env
# ===== KOOK Bot 基本配置 =====
KOOK_WS_TOKEN=your_kook_bot_token_here         # KOOK Bot 的 WebSocket Token
KOOK_BOT_ID=your_bot_id_here                   # 本 Bot 的 ID
KOOK_CHANNEL_ID=                               # 指定频道ID（留空则全频道响应）

# ===== 第三方API客户端配置 =====
THIRD_PARTY_API_URL=https://api.zmone.me/v1    # 第三方API基础URL
THIRD_PARTY_API_KEY=your_api_key_here          # API密钥
THIRD_PARTY_API_TIMEOUT=30                     # 请求超时时间
THIRD_PARTY_API_MAX_RETRIES=3                  # 最大重试次数

# ===== 主模型配置（用于对话生成） =====
SF_APIKEY=your_primary_api_key_here            # 主模型API密钥
SF_APIURL=https://api.zmone.me/v1              # 主模型API地址
SF_MODEL=gpt-4.1-mini                          # 主模型名称

# ===== 第二模型配置（备用模型） =====
SECONDARY_APIKEY=your_secondary_api_key        # 第二模型API密钥
SECONDARY_APIURL=https://api.zmone.me/v1       # 第二模型API地址
SECONDARY_MODEL=DeepSeek-V3                    # 第二模型名称

# ===== MongoDB配置（可选） =====
MONGODB_URI=mongodb://localhost:27017          # MongoDB连接URI
MONGODB_DATABASE=maimai_bot                    # 数据库名称
ENABLE_MONGODB=false                           # 是否启用MongoDB

# ===== 人格系统配置 =====
DEFAULT_PERSONA=default                        # 默认人格模板
PERSONA_ADAPTATION_RATE=0.2                    # 人格适应速率
PERSONA_MEMORY_DAYS=30                         # 人格记忆保留天数
```

### 启动机器人

```bash
# 激活虚拟环境（如果使用）
source kook_bot_env/bin/activate

# 启动机器人
python bot.py
```

## 💬 使用指南

### 基本交互方式

**群聊交互**：
```
用户: @机器人 你好！           # 触发并进入连续对话模式
机器人: 你好！很高兴见到你~     # 回复并设置180秒连续对话
用户: 今天天气怎么样？         # 无需@，直接对话（连续模式）
机器人: [天气信息...]         # 继续回复，重置计时器
用户: 谢谢                   # 仍在连续对话中
```

**私聊交互**：
```
用户: 你好                   # 私聊无需唤醒词
机器人: 你好！有什么可以帮助你的吗？
用户: 帮我记住今天是我生日      # 知识学习功能
机器人: 好的，我已经记住了！
```

**唤醒词触发**：
```
用户: 麦麦，来聊聊天          # 使用唤醒词触发
机器人: 好呀！想聊什么？       # 进入连续对话模式
用户: 你会什么？             # 连续对话中
```

### 特殊功能

**辱骂检测与反击**：
- 机器人会自动检测辱骂性语言
- 根据辱骂程度选择合适的反击方式
- 支持多种反击风格（霸气、讽刺、调皮等）

**知识记忆**：
- 使用"记住xxx"让机器人学习信息
- 机器人会自动关联相关知识
- 支持用户个人信息管理

**情感反馈**：
- 使用 👍 或 👎 对回复进行评价
- 机器人会根据反馈调整回复风格
- 支持情感状态识别和响应

### 命令列表

| 命令 | 功能描述 | 使用示例 |
|------|---------|----------|
| `/reset` | 重置与用户的对话历史 | `/reset` |
| `/ping` | 检查机器人运行状态和运行时间 | `/ping` |
| `记住xxx` | 让机器人记住特定信息 | `记住我喜欢吃苹果` |
| `麦麦` | 唤醒词，在群聊中触发对话 | `麦麦，你好` |

### 反馈系统

- **👍 点赞** - 表示回复满意，机器人会学习优秀回复模式
- **👎 点踩** - 表示回复不满意，机器人会调整回复策略
- **情感识别** - 自动识别用户情绪并给出相应回应

## 📁 项目结构

```
kook-bot/
├── bot.py                          # 🚀 主程序入口
├── api_client.py                   # 🔌 第三方API客户端
├── .env                           # ⚙️ 环境变量配置
├── .env.example                   # 📋 环境变量示例
├── CHANGELOG.md                   # 📝 更新日志
├── README.md                      # 📖 项目说明
├── requirements.txt               # 📦 依赖列表
│
├── agents/                        # 🤖 智能体模块
│   ├── __init__.py
│   ├── thinking_agent.py          # 💭 思考链Agent
│   ├── advanced_emotion_agent.py  # 😊 情感分析Agent
│   ├── enhanced_dialogue_agent.py # 💬 对话生成Agent
│   ├── personality_agent.py       # 🎭 人格系统Agent
│   └── insult_detection_agent.py  # 🛡️ 辱骂检测Agent
│
├── database/                      # 💾 数据库模块
│   ├── __init__.py
│   ├── mongodb_client.py          # 🍃 MongoDB客户端
│   ├── models.py                  # 📊 数据模型
│   └── migration.py               # 🔄 数据迁移
│
├── data/                          # 📚 数据存储
│   ├── users.json                 # 👥 用户数据
│   ├── knowledge.json             # 🧠 知识库
│   └── personality_templates.json # 🎭 人格模板
│
└── khl/                          # 📡 KOOK SDK
    ├── bot/                      # 🤖 机器人核心
    ├── command/                  # ⌨️ 命令系统
    └── ...                       # 其他SDK模块
```

## 🔧 技术特性

### 🤖 多Agent智能体系统

**协作架构**：
- **思考链Agent** - 分析用户意图，制定回复策略
- **情感分析Agent** - 识别情感状态，调整回复风格
- **对话生成Agent** - 生成自然流畅的回复内容
- **人格系统Agent** - 维持一致的对话人格
- **辱骂检测Agent** - 识别并反击不当言论

**智能决策**：
- 多Agent协同决策，提供更精准的回复
- 动态调整Agent权重，适应不同对话场景
- 上下文感知，保持对话连贯性

### 🛡️ 辱骂检测系统

**检测机制**：
- **关键词匹配** - 150+辱骂词汇库，包含各种变形
- **正则模式** - 防止字符替换、空格插入等绕过技巧
- **语义分析** - 结合LLM进行语义层面的辱骂识别

**反击策略**：
- **风格多样** - 25+种反击模板（霸气、讽刺、调皮、毒舌等）
- **个性化** - 基于LLM生成符合"孙吧老哥"风格的反击
- **分级响应** - 根据辱骂严重程度选择合适的反击强度

### 💬 连续对话机制

**智能触发**：
- **@触发** - 被@后自动进入连续对话模式
- **唤醒词** - 使用"麦麦"在群聊中触发
- **私聊模式** - 私聊中无需触发词，直接对话

**状态管理**：
- **180秒窗口** - 触发后180秒内可连续对话
- **自动延长** - 每次对话都会重置计时器
- **用户隔离** - 不同用户的对话状态独立管理

### 🔧 配置化设计

**环境驱动**：
- **灵活配置** - 所有关键参数都可通过.env文件调整
- **多模型支持** - 支持OpenAI、DeepSeek等多种LLM
- **API切换** - 轻松切换不同的API提供商

**扩展性**：
- **模块化架构** - 易于添加新的Agent和功能
- **插件机制** - 支持第三方功能扩展
- **数据库可选** - 支持JSON文件或MongoDB存储

## 🚀 性能优化

### 并发控制
- **自适应信号量** - 根据响应时间动态调整并发数
- **请求队列** - 合理排队避免API限流
- **超时控制** - 防止长时间等待

### 内存管理
- **LRU缓存** - 智能缓存频繁访问的数据
- **定期清理** - 自动清理过期的对话状态
- **资源释放** - 及时释放不需要的连接和资源

## 🛠️ 开发指南

### 添加新Agent

1. **创建Agent类**：
```python
# agents/your_agent.py
class YourAgent:
    async def process(self, message, context):
        # 处理逻辑
        return result
```

2. **注册Agent**：
```python
# bot.py 中添加
your_agent = YourAgent()
```

3. **集成到流程**：
```python
# 在消息处理流程中调用
result = await your_agent.process(message, context)
```

### 自定义反击模板

编辑 `agents/insult_detection_agent.py` 中的 `INSULT_RESPONSES` 字典：

```python
INSULT_RESPONSES = {
    "your_style": [
        "你的反击模板1",
        "你的反击模板2",
        # ...
    ]
}
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！无论是功能建议、Bug报告还是代码贡献。

### 贡献流程

1. **Fork项目** - 点击右上角Fork按钮
2. **创建分支** - `git checkout -b feature/amazing-feature`
3. **提交更改** - `git commit -m 'Add some amazing feature'`
4. **推送分支** - `git push origin feature/amazing-feature`
5. **创建PR** - 打开Pull Request

### 开发规范

- **代码风格** - 遵循PEP 8 Python编码规范
- **注释完整** - 为复杂逻辑添加清晰注释
- **测试覆盖** - 为新功能添加相应测试
- **文档更新** - 更新README和相关文档

### 功能建议

- 🎯 **新Agent** - 设计新的智能体功能
- 🔧 **性能优化** - 提升响应速度和稳定性
- 🎨 **UI改进** - 改善用户交互体验
- 🌐 **国际化** - 支持多语言
- 📊 **数据分析** - 对话质量分析功能

## 📞 支持与反馈

### 获取帮助

- **📚 文档** - 查看README和代码注释
- **💬 社区** - 加入KOOK交流频道：https://kook.vip/izhvYt
- **🐛 问题报告** - 在GitHub Issues中报告Bug
- **💡 功能建议** - 通过Issues提出新功能需求

### 常见问题

**Q: 机器人不响应消息？**
A: 检查Token配置、网络连接和权限设置

**Q: API调用失败？**
A: 确认API密钥有效，检查账户余额和配额

**Q: 内存占用过高？**
A: 定期重启，检查对话历史清理设置

**Q: 如何添加自定义功能？**
A: 参考开发指南，创建新的Agent模块

## 📄 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新历史。

### 最新版本 v1.2.0 (2025-05-29)

- ✨ 新增智能辱骂检测与反击系统
- 🔄 优化连续对话机制，支持180秒无缝对话
- ⚙️ 第三方API客户端支持环境变量配置
- 🛠️ 修复私信触发逻辑
- 📚 完善人格模板和回复质量
- 🧹 代码结构优化和清理

## 📋 待办事项

- [ ] 🌍 多语言支持
- [ ] 📊 对话质量分析仪表板
- [ ] 🔌 插件系统开发
- [ ] 🎨 Web管理界面
- [ ] 📱 移动端适配
- [ ] 🔒 高级权限系统
- [ ] 📈 性能监控和报警

## 🙏 致谢

感谢以下开源项目和贡献者：

- **[khl.py](https://github.com/TWT233/khl.py)** - 优秀的KOOK Python SDK
- **[OpenAI API](https://openai.com/)** - 强大的LLM服务
- **[Rich](https://github.com/Textualize/rich)** - 美观的终端输出
- **所有贡献者** - 感谢每一位为项目贡献代码和建议的开发者

## 📜 许可证

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

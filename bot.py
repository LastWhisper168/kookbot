import os
import random
import json
import time
import datetime
import re
import asyncio
import aiohttp
import numpy as np
from khl import Bot, Message, EventTypes, Event
from rich.console import Console
from rich.markup import escape
from dotenv import load_dotenv

# 导入 API 客户端
from api_client import third_party_api_call, cleanup_api_client, ApiResponse

# 导入新的Agent类
from agents.thinking_agent import ThinkingAgent
from agents.advanced_emotion_agent import AdvancedEmotionAgent
from agents.enhanced_dialogue_agent import EnhancedDialogueAgent
from agents.personality_agent import PersonalityAgent
from agents.insult_detection_agent import InsultDetectionAgent

# 导入数据库模块
from database.mongodb_client import init_mongodb, close_mongodb, get_mongodb_client
from database.models import UserProfile, EmotionHistory
from database.migration import run_migration

# 加载环境变量
load_dotenv()
console = Console()
START_TIME = time.time()

# 基本配置
BOT_TOKEN = os.getenv("KOOK_WS_TOKEN")
BOT_ID = os.getenv("KOOK_BOT_ID")
OTHER_BOT_ID = os.getenv("OTHER_BOT_ID")
KOOK_CHANNEL_ID = os.getenv("KOOK_CHANNEL_ID", "")

# AI 接口配置
PRIMARY_API_KEY = os.getenv("PRIMARY_API_KEY")
PRIMARY_API_URL = os.getenv("PRIMARY_API_URL")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL")
SECONDARY_API_KEY = os.getenv("SECONDARY_API_KEY")
SECONDARY_API_URL = os.getenv("SECONDARY_API_URL")
SECONDARY_MODEL = os.getenv("SECONDARY_MODEL")

# MongoDB 配置
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "maimai_bot")
ENABLE_MONGODB = os.getenv("ENABLE_MONGODB", "false").lower() == "true"
mongodb_enabled = ENABLE_MONGODB

# 人格系统配置
DEFAULT_PERSONA = os.getenv("DEFAULT_PERSONA", "default")
PERSONA_ADAPTATION_RATE = float(os.getenv("PERSONA_ADAPTATION_RATE", "0.2"))
PERSONA_MEMORY_DAYS = int(os.getenv("PERSONA_MEMORY_DAYS", "30"))

# 性能调优配置
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "5"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
MAX_HISTORY_LENGTH = int(os.getenv("MAX_HISTORY_LENGTH", "20"))

# 全局并发信号量，用于限制并发处理
message_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

# 环境变量检查
if not BOT_TOKEN or not PRIMARY_API_KEY or not PRIMARY_API_URL:
    console.print("[red]必要环境变量未设置完整[/red]")
    raise SystemExit(1)

# 初始化 Bot
bot = Bot(token=BOT_TOKEN)
console.print("[green]KOOK 机器人已初始化[/green]")

# Bot 自身状态
bot_state = {
    "doing": "idle",
    "thinking": "",
    "want_reply": True,
    "want_send_more": False,
}
# 唤醒后保持对话状态3分钟
last_wake = {}
WAKE_TIMEOUT = 180  # seconds


async def cleanup_expired_conversations():
    """清理过期的连续对话状态"""
    while True:
        try:
            current_time = time.time()
            expired_users = []

            for uid, wake_time in last_wake.items():
                if current_time - wake_time > WAKE_TIMEOUT:
                    expired_users.append(uid)

            for uid in expired_users:
                del last_wake[uid]
                console.print(f"[dim]🕐 用户 {uid} 的连续对话状态已过期[/dim]")

            # 每30秒清理一次
            await asyncio.sleep(30)
        except Exception as e:
            console.print(f"[red]清理过期对话状态时出错: {e}[/red]")
            await asyncio.sleep(30)


# 弹性并发控制：根据平均延迟自动伸缩
from collections import deque


class AdaptiveSemaphore:
    def __init__(self, initial=5, min_limit=1, max_limit=20):
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.limit = initial
        self._semaphore = asyncio.Semaphore(initial)
        self.latencies = deque(maxlen=50)

    async def acquire(self):
        await self._semaphore.acquire()

    def release(self):
        self._semaphore.release()

    def record(self, latency):
        self.latencies.append(latency)
        if self.latencies:
            avg = sum(self.latencies) / len(self.latencies)
            # 根据平均延迟调整限流
            if avg < 1.0 and self.limit < self.max_limit:
                self.limit += 1
                self._semaphore = asyncio.Semaphore(self.limit)
            elif avg > 2.0 and self.limit > self.min_limit:
                self.limit -= 1
                self._semaphore = asyncio.Semaphore(self.limit)


adaptive_sem = AdaptiveSemaphore(
    initial=MAX_CONCURRENCY, min_limit=1, max_limit=MAX_CONCURRENCY * 4
)

# 本地存储路径
USERS_FILE = "data/users.json"
KB_FILE = "data/knowledge.json"
os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)

# 加载或初始化数据
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users_data = json.load(f)
else:
    users_data = {}

if os.path.exists(KB_FILE):
    with open(KB_FILE, "r", encoding="utf-8") as f:
        knowledge_store = json.load(f)
else:
    knowledge_store = []

MAX_HISTORY = MAX_HISTORY_LENGTH


# 保存数据函数
def save_knowledge():
    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump(knowledge_store, f, ensure_ascii=False, indent=2)


async def save_history():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)


async def safe_reply(msg: Message, text: str):
    try:
        console.print(f"[cyan]尝试回复消息，频道类型: {msg.channel_type}[/cyan]")

        # 直接使用channel.send方法发送消息
        await msg.ctx.channel.send(text)
        console.print(f"[green]消息发送成功[/green]")
    except Exception as e:
        console.print(f"[red]消息发送失败: {e}[/red]")
        try:
            # 尝试使用reply方法作为备选
            console.print("[yellow]尝试使用reply方法...[/yellow]")
            await msg.reply(text)
            console.print("[green]使用reply方法发送成功[/green]")
        except Exception as e2:
            console.print(f"[red]所有发送方式都失败: {e2}[/red]")


# --- LLM 客户端 ---
class LLMClient:
    def __init__(self, key, url, model):
        self.key = key
        self.url = url
        self.model = model
        self.session = None

    async def chat(self, messages):
        # 设置请求超时，防止长时间挂起
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        if self.session is None:
            import ssl, certifi

            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
            # 在创建 Session 时指定超时
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        console.print(f"[magenta]调用模型: {self.model} at {self.url}[/magenta]")
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "messages": messages}
        try:
            # 使用超时保护，防止请求无限挂起
            async with self.session.post(
                f"{self.url}/chat/completions", headers=headers, json=payload
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except asyncio.TimeoutError:
            console.print(f"[red]模型请求超时（>60s），跳过本次调用[/red]")
            raise
        except Exception as e:
            console.print(f"[red]模型调用异常: {e}[/red]")
            raise

    async def close(self):
        if self.session:
            await self.session.close()


# --- 双智能体多Agent系统 ---
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class DialogueContext:
    user_id: str
    message: str
    history: List[Dict[str, str]]
    metadata: Dict[str, Any] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RetrievalResult:
    success: bool
    data: Any = None
    error: str = None
    response_time: float = None
    source: str = None


class Agent:
    async def handle(self, payload):
        raise NotImplementedError


class RetrievalAgent(Agent):
    def __init__(self, llm):
        self.llm = llm

    async def handle(self, payload):
        console.print(f"[cyan]RetrievalAgent 模型：{self.llm.model}[/cyan]")
        prompt = f"你是知识检索助手，用户问题：{payload['text']}"
        try:
            resp = await self.llm.chat([{"role": "system", "content": prompt}])
            text = resp["choices"][0]["message"]["content"].strip()
            return {"contexts": [text]}
        except Exception as e:
            console.print(f"[red]检索失败：{e}，跳过检索[/red]")
            return {"contexts": []}


class GenerationAgent(Agent):
    def __init__(self, llm):
        self.llm = llm

    async def handle(self, payload):
        console.print(f"[cyan]GenerationAgent 模型：{self.llm.model}[/cyan]")
        ctx = payload.get("contexts", [])
        history = payload.get("history", [])
        text = payload.get("text", "")
        emotion = payload.get("emotion", "neutral")
        thinking_process = payload.get("thinking_process", "")
        persona = payload.get("persona", "")

        # 构建系统提示词
        system_prompt = f"""你是一个充满活力和亲和力的AI助手。{persona}

当前用户情绪: {emotion}
思考过程: {thinking_process[:200] if thinking_process else '无'}

请根据用户的情绪状态和对话历史，给出恰当的回复。"""

        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史对话
        for h in history[-10:]:  # 只保留最近10条
            messages.append({"role": h["role"], "content": h["content"]})

        # 添加当前消息
        messages.append({"role": "user", "content": text})

        try:
            resp = await self.llm.chat(messages)
            return {"response": resp["choices"][0]["message"]["content"].strip()}
        except Exception as e:
            console.print(f"[red]生成失败：{e}[/red]")
            return {"response": "抱歉，我现在有点困惑，请稍后再试！"}


class FeedbackAgent(Agent):
    async def handle(self, payload):
        fb = payload.get("feedback")
        uid = payload.get("user")
        if fb:
            users_data.setdefault(uid, {}).setdefault("feedback", []).append(
                {"time": datetime.datetime.utcnow().isoformat(), "feedback": fb}
            )
        return {}


class BotStateAgent(Agent):
    async def handle(self, payload):
        return {"state": bot_state.copy()}


class EnhancedDispatcher:
    """增强版调度器 - 集成思维链、高级情感分析、增强对话生成和MongoDB存储"""

    def __init__(self, agents):
        self.agents = agents
        self.mongodb_client = get_mongodb_client()

    async def dispatch(self, uid, text, history, feedback=None):
        console.print("[yellow]🧠 启动增强对话流程...[/yellow]")

        try:
            # 1. 高级情感分析
            console.print("[cyan]📊 开始情感分析...[/cyan]")
            emotion_result = await self.agents["emotion"].handle(
                {"user": uid, "text": text}
            )
            emotion = emotion_result.get("emotion", "neutral")
            emoji = emotion_result.get("emoji", "")
            intensity = emotion_result.get("intensity", 0.7)

            console.print(
                f"[green]😊 情感分析完成: {emotion} {emoji} (强度: {intensity})[/green]"
            )

            # MongoDB存储情感记录
            if (
                mongodb_enabled
                and self.mongodb_client
                and self.mongodb_client.is_connected
            ):
                from database.models import EmotionHistory

                emotion_entry = EmotionHistory(
                    user_id=uid,
                    emotion=emotion,
                    emoji=emoji,
                    intensity=intensity,
                    text=text,
                )
                await self.mongodb_client.save_emotion(emotion_entry)
                console.print("[green]📊 情感记录已保存到MongoDB[/green]")

            # 2. 生成思考链
            console.print("[cyan]🤔 开始思考过程生成...[/cyan]")
            thinking_result = await self.agents["thinking"].handle({"text": text})
            thinking_process = thinking_result.get("thinking_process", "")
            conclusion = thinking_result.get("conclusion", "")

            console.print(
                f"[green]🧠 思考过程已生成 (长度: {len(thinking_process)}字符)[/green]"
            )

            # 3. 知识检索
            console.print("[cyan]🔍 开始知识检索...[/cyan]")
            ctx = await self.agents["retrieval"].handle({"text": text})

            # 4. 获取人格指令
            console.print("[cyan]👤 获取人格指令...[/cyan]")
            personality_result = await self.agents["personality"].handle(
                {"user": uid, "text": text, "emotion": emotion}
            )
            persona_instruction = personality_result.get("persona", "")
            persona_name = personality_result.get("name", "麦麦")

            console.print(f"[green]👤 使用人格: {persona_name}[/green]")

            # 5. 增强对话生成
            console.print("[cyan]💬 开始增强对话生成...[/cyan]")
            res = await self.agents["generation"].handle(
                {
                    "contexts": ctx["contexts"],
                    "history": history,
                    "text": text,
                    "emotion": emotion,
                    "emoji": emoji,
                    "intensity": intensity,
                    "thinking_process": thinking_process,
                    "conclusion": conclusion,
                    "persona": persona_instruction,
                }
            )

            # 6. 知识存储处理
            if text.startswith("记住"):
                fact = text[2:].strip()
                # 存储到本地JSON（兼容模式）
                entry = {
                    "user": uid,
                    "time": datetime.datetime.utcnow().isoformat(),
                    "fact": fact,
                    "emotion": emotion,
                    "thinking": thinking_process[:200] if thinking_process else "",
                }
                knowledge_store.append(entry)
                save_knowledge()

                # 存储到MongoDB
                if (
                    mongodb_enabled
                    and self.mongodb_client
                    and self.mongodb_client.is_connected
                ):
                    from database.models import KnowledgeEntry

                    knowledge_entry = KnowledgeEntry(
                        user_id=uid,
                        fact=fact,
                        emotion=emotion,
                        thinking_process=(
                            thinking_process[:200] if thinking_process else ""
                        ),
                    )
                    await self.mongodb_client.add_knowledge(knowledge_entry)
                    console.print("[green]📝 知识已保存到MongoDB[/green]")
                else:
                    console.print("[green]📝 知识已保存到本地JSON[/green]")

            # 7. 反馈处理
            if feedback:
                await self.agents["feedback"].handle(
                    {"feedback": feedback, "user": uid}
                )

                # 存储到MongoDB
                if (
                    mongodb_enabled
                    and self.mongodb_client
                    and self.mongodb_client.is_connected
                ):
                    from database.models import FeedbackEntry

                    feedback_type = (
                        "positive" if feedback.startswith("👍") else "negative"
                    )
                    feedback_entry = FeedbackEntry(
                        user_id=uid,
                        feedback_type=feedback_type,
                        content=feedback,
                        context=text,
                    )
                    await self.mongodb_client.save_feedback(feedback_entry)
                    console.print("[green]💭 反馈已保存到MongoDB[/green]")

            # 8. 更新状态
            bot_state["doing"] = "responding"
            bot_state["thinking"] = conclusion[:100] if conclusion else ""

            return res

        except Exception as e:
            console.print(f"[red]调度器错误: {e}[/red]")
            return {"response": "抱歉，我遇到了一些问题，请稍后再试。"}
        finally:
            bot_state["doing"] = "idle"


# 初始化 LLM 客户端
primary_llm = LLMClient(PRIMARY_API_KEY, PRIMARY_API_URL, PRIMARY_MODEL)
secondary_llm = LLMClient(SECONDARY_API_KEY, SECONDARY_API_URL, SECONDARY_MODEL)

# 初始化所有 Agent
agents = {
    "retrieval": RetrievalAgent(primary_llm),
    # 使用 EnhancedDialogueAgent 生成更自然的人类式回复
    "generation": EnhancedDialogueAgent(secondary_llm),
    "feedback": FeedbackAgent(),
    "state": BotStateAgent(),
    "thinking": ThinkingAgent(primary_llm),
    "emotion": AdvancedEmotionAgent(primary_llm),
    "personality": PersonalityAgent(),
    "insult_detection": InsultDetectionAgent(primary_llm),
}

# 初始化调度器
dispatcher = EnhancedDispatcher(agents)


# 消息处理函数
@bot.on_message()
async def handle_message(msg: Message):
    """处理所有文本消息"""
    # 过滤条件
    if msg.author_id == BOT_ID:  # 忽略自己的消息
        return

    if OTHER_BOT_ID and msg.author_id == OTHER_BOT_ID:  # 忽略其他机器人
        return

    # 检查频道限制（仅对公共频道消息生效）
    if (
        KOOK_CHANNEL_ID
        and hasattr(msg, "channel_id")
        and msg.channel_id != KOOK_CHANNEL_ID
    ):
        return
    # 获取消息内容
    text = msg.content.strip()
    if not text:
        return
    # 添加调试信息 - 显示频道类型
    console.print(
        f"[cyan]消息类型: {msg.channel_type}, 消息内容: {text[:30]}...[/cyan]"
    )
    # 检查触发条件
    is_mentioned = f"(met){BOT_ID}(met)" in msg.content
    # 两种方式判断是否是私信
    is_private = (
        str(msg.channel_type) == "ChannelPrivacyTypes.PERSON"
        or msg.channel_type == "PERSON"
    )
    is_wakeword = "麦麦" in text

    # 获取用户ID，用于连续对话管理
    uid = msg.author_id
    current_time = time.time()

    # 检查是否在连续对话状态中
    is_in_conversation = (
        uid in last_wake and (current_time - last_wake[uid]) <= WAKE_TIMEOUT
    )

    # 添加调试信息
    if is_private:
        console.print(f"[yellow]📱 收到私信: {text[:50]}... (来自: {uid})[/yellow]")
    else:
        console.print(
            f"[blue]💬 群聊消息 - @机器人: {is_mentioned}, 唤醒词: {is_wakeword}, 连续对话: {is_in_conversation}[/blue]"
        )

    # 判断是否应该响应消息
    should_respond = (
        is_private  # 私聊总是响应
        or is_mentioned  # 被@时响应
        or is_wakeword  # 包含唤醒词时响应
        or is_in_conversation  # 在连续对话状态中响应
    )

    if not should_respond:
        return  # 不满足响应条件，忽略消息

    # 更新唤醒时间（任何触发响应的情况都会延长连续对话时间）
    last_wake[uid] = current_time

    # 显示连续对话状态
    if is_in_conversation:
        remaining_time = int(
            WAKE_TIMEOUT - (current_time - last_wake[uid]) + WAKE_TIMEOUT
        )  # 重新计算剩余时间
        console.print(
            f"[green]🔄 连续对话模式: 用户 {uid} (剩余时间: {remaining_time}秒)[/green]"
        )
    elif is_mentioned or is_wakeword:
        console.print(
            f"[green]🎯 触发对话: 用户 {uid} 进入连续对话模式 ({WAKE_TIMEOUT}秒)[/green]"
        )
    elif is_private:
        console.print(f"[green]💌 私聊模式: 用户 {uid} (持续响应)[/green]")

    # 清理@标记
    text = text.replace(f"(met){BOT_ID}(met)", "").strip()
    # 使用并发控制
    async with message_semaphore:
        try:
            console.print(f"[blue]收到消息: {text} (来自: {msg.author_id})[/blue]")

            # 首先检测是否包含辱骂
            insult_result = await agents["insult_detection"].handle({"text": text})

            if insult_result["is_insult"]:
                console.print(
                    f"[red]检测到辱骂行为，反击等级: {insult_result['insult_level']}[/red]"
                )
                response = insult_result["response"]

                # 直接发送反击回复，不需要经过其他Agent处理
                await safe_reply(msg, response)

                # 记录到历史（可选）
                uid = msg.author_id
                user_data = users_data.get(uid, {"history": []})
                history = user_data.get("history", [])
                history.append({"role": "user", "content": text})
                history.append({"role": "assistant", "content": response})

                # 保持历史记录在限制范围内
                if len(history) > MAX_HISTORY * 2:
                    history = history[-(MAX_HISTORY * 2) :]

                user_data["history"] = history
                user_data["last_message"] = time.time()
                users_data[uid] = user_data

                # 异步保存历史
                asyncio.create_task(save_history())
                return

            # 如果不是辱骂，按正常流程处理
            # 获取用户历史
            uid = msg.author_id
            user_data = users_data.get(uid, {"history": []})
            history = user_data.get("history", [])

            # 调用调度器处理消息
            start_time = time.time()
            result = await dispatcher.dispatch(uid, text, history)
            response = result.get("response", "抱歉，我现在无法回复。")

            # 记录延迟
            latency = time.time() - start_time
            adaptive_sem.record(latency)
            console.print(f"[green]响应时间: {latency:.2f}秒[/green]")

            # 发送回复
            await safe_reply(msg, response)

            # 更新历史记录
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": response})

            # 保持历史记录在限制范围内
            if len(history) > MAX_HISTORY * 2:
                history = history[-(MAX_HISTORY * 2) :]

            # 更新用户数据
            user_data["history"] = history
            user_data["last_message"] = time.time()
            users_data[uid] = user_data

            # 异步保存历史
            asyncio.create_task(save_history())

        except Exception as e:
            console.print(f"[red]处理消息时出错: {e}[/red]")
            await safe_reply(msg, "抱歉，处理您的消息时出现了错误。")


# Bot 启动和关闭处理
@bot.on_startup
async def on_startup(bot):
    """Bot 启动时执行"""
    console.print("[green]🚀 Bot 正在启动...[/green]")

    # 初始化 MongoDB（如果启用）
    if mongodb_enabled:
        try:
            await init_mongodb(MONGODB_URI)
            console.print("[green]📊 MongoDB 已连接[/green]")

            # 运行数据库迁移
            await run_migration()
            console.print("[green]🔄 数据库迁移完成[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ MongoDB 连接失败: {e}，将使用本地存储[/yellow]")

    # 启动清理过期对话状态的后台任务
    asyncio.create_task(cleanup_expired_conversations())
    console.print("[green]🧹 对话状态清理任务已启动[/green]")

    console.print(f"[green]✅ Bot 启动完成！[/green]")
    console.print(f"[cyan]📊 并发限制: {MAX_CONCURRENCY}[/cyan]")
    console.print(f"[cyan]⏰ 连续对话超时: {WAKE_TIMEOUT}秒[/cyan]")
    console.print(f"[cyan]💬 触发方式: @机器人 | 私聊 | 唤醒词'麦麦' | 连续对话[/cyan]")


@bot.on_shutdown
async def on_shutdown():
    """Bot 关闭时执行"""
    console.print("[yellow]Bot 正在关闭...[/yellow]")

    # 保存数据
    await save_history()
    save_knowledge()

    # 关闭 LLM 客户端
    await primary_llm.close()
    await secondary_llm.close()

    # 关闭 MongoDB 连接
    if mongodb_enabled:
        await close_mongodb()

    # 清理 API 客户端
    await cleanup_api_client()

    console.print("[red]Bot 已关闭[/red]")


# 主程序入口
if __name__ == "__main__":
    console.print("[cyan]=" * 50 + "[/cyan]")
    console.print("[cyan]KOOK AI Bot - v1.1.0[/cyan]")
    console.print("[cyan]=" * 50 + "[/cyan]")

    # 运行 Bot
    bot.run()

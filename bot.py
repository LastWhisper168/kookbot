import os
import random
import json
import time
import datetime
import re
import asyncio
import aiohttp
import numpy as np
# 全局并发信号量，用于限制并发处理
message_semaphore = asyncio.Semaphore(5)
from khl import Bot, Message
from rich.console import Console
from rich.markup import escape
from dotenv import load_dotenv
# 导入 API 客户端
from api_client import zmone_api_call, cleanup_api_client, ApiResponse

# 加载环境变量
load_dotenv()
console = Console()
START_TIME = time.time()

# 基本配置
BOT_TOKEN      = os.getenv("KOOK_WS_TOKEN")
BOT_ID         = os.getenv("KOOK_BOT_ID")
OTHER_BOT_ID   = os.getenv("OTHER_BOT_ID")

# AI 接口配置
PRIMARY_API_KEY   = os.getenv("SF_APIKEY")
PRIMARY_API_URL   = os.getenv("SF_APIURL")
PRIMARY_MODEL     = os.getenv("SF_MODEL")
SECONDARY_API_KEY = os.getenv("SECONDARY_APIKEY")
SECONDARY_API_URL = os.getenv("SECONDARY_APIURL")
SECONDARY_MODEL   = os.getenv("SECONDARY_MODEL")

# 环境变量检查
if not BOT_TOKEN or not PRIMARY_API_KEY or not PRIMARY_API_URL:
    console.print("[red]必要环境变量未设置完整[/red]")
    raise SystemExit(1)

# 初始化 Bot
bot = Bot(token=BOT_TOKEN)
console.print("[green]KOOK Bot 已初始化[/green]")

# Bot 自身状态
bot_state = {
    'doing': 'idle',
    'thinking': '',
    'want_reply': True,
    'want_send_more': False
}
# 唤醒后保持对话状态3分钟
last_wake = {}
WAKE_TIMEOUT = 180  # seconds

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
        avg = sum(self.latencies) / len(self.latencies)
        # 根据平均延迟调整限流
        if avg < 1.0 and self.limit < self.max_limit:
            self.limit += 1
            self._semaphore = asyncio.Semaphore(self.limit)
        elif avg > 2.0 and self.limit > self.min_limit:
            self.limit -= 1
            self._semaphore = asyncio.Semaphore(self.limit)

adaptive_sem = AdaptiveSemaphore(initial=5, min_limit=1, max_limit=20)

# 本地存储路径
USERS_FILE = "data/users.json"
KB_FILE    = "data/knowledge.json"
os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)

# 加载或初始化数据
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        users_data = json.load(f)
else:
    users_data = {}

if os.path.exists(KB_FILE):
    with open(KB_FILE, 'r', encoding='utf-8') as f:
        knowledge_store = json.load(f)
else:
    knowledge_store = []

MAX_HISTORY = 20

# 保存数据函数
def save_knowledge():
    with open(KB_FILE, 'w', encoding='utf-8') as f:
        json.dump(knowledge_store, f, ensure_ascii=False, indent=2)

async def save_history():
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)

async def safe_reply(msg: Message, text: str):
    try:
        await msg.reply(text)
    except Exception as e:
        console.print(f"[red]消息发送失败: {e}[/red]")

# --- LLM 客户端 ---
class LLMClient:
    def __init__(self, key, url, model):
        self.key = key
        self.url = url
        self.model = model
        self.session = None

    async def chat(self, messages):
        # 设置请求超时，防止长时间挂起
        timeout = aiohttp.ClientTimeout(total=60)
        if self.session is None:
            import ssl, certifi
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
            # 在创建 Session 时指定超时
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        console.print(f"[magenta]调用模型: {self.model} at {self.url}[/magenta]")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages}
        try:
            # 使用超时保护，防止请求无限挂起
            async with self.session.post(f"{self.url}/chat/completions", headers=headers, json=payload) as resp:
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
        if self.session is None:
            import ssl, certifi
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
            self.session = aiohttp.ClientSession(connector=connector)
        console.print(f"[magenta]调用模型: {self.model} at {self.url}[/magenta]")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": messages}
        async with self.session.post(f"{self.url}/chat/completions", headers=headers, json=payload) as resp:
            resp.raise_for_status()
            return await resp.json()

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
            text = resp['choices'][0]['message']['content'].strip()
            return {'contexts': [text]}
        except Exception as e:
            console.print(f"[red]检索失败：{e}，跳过检索[/red]")
            return {'contexts': []}

class DialogueAgent(Agent):
    """主智能体 - 负责对话生成和上下文维护"""
    def __init__(self, llm):
        self.llm = llm

    async def handle(self, payload):
        persona = (
            "你是“麦麦”，一个活泼、幽默、善于关心用户的二次元俏皮小女孩。"
            "你的回复要带点俏皮、带 emoji，让人感觉像在和朋友聊天。"
        )
        sys_prompt = persona + "\n参考信息：\n" + "\n".join(f"- {c}" for c in payload['contexts'])
        sys_prompt += f"\n用户情绪：{payload.get('emotion','neutral')}"
        messages = [{"role": "system", "content": sys_prompt}] + payload['history'] + [{"role": "user", "content": payload['text']}]
        resp = await self.llm.chat(messages)
        return {'reply': resp['choices'][0]['message']['content'].strip()}

class FeedbackAgent(Agent):
    async def handle(self, payload):
        fb = payload.get('feedback')
        uid = payload.get('user')
        if fb:
            users_data.setdefault(uid, {}).setdefault('feedback', []).append({
                'time': datetime.datetime.utcnow().isoformat(),
                'feedback': fb
            })
        return {}

class EmotionAgent(Agent):
    async def handle(self, payload):
        uid = payload['user']
        txt = payload['text']
        emo = users_data.setdefault(uid, {}).get('emotion', 'neutral')
        if any(w in txt for w in ['开心', '快乐']):
            emo = 'happy'
        elif any(w in txt for w in ['难过', '悲伤']):
            emo = 'sad'
        users_data[uid]['emotion'] = emo
        return {'emotion': emo}

class BotStateAgent(Agent):
    async def handle(self, payload):
        return {'state': bot_state.copy()}

class Dispatcher:
    def __init__(self, agents):
        self.agents = agents

    async def dispatch(self, uid, text, history, feedback=None):
        emo = (await agents_map['emotion'].handle({'user': uid, 'text': text}))['emotion']
        ctx = await self.agents['retrieval'].handle({'text': text})
        res = await self.agents['generation'].handle({
            'contexts': ctx['contexts'],
            'history': history,
            'text': text,
            'emotion': emo
        })
        if text.startswith('记住'):
            entry = {
                'user': uid,
                'time': datetime.datetime.utcnow().isoformat(),
                'fact': text[2:].strip()
            }
            knowledge_store.append(entry)
            save_knowledge()
        if feedback:
            await self.agents['feedback'].handle({'feedback': feedback, 'user': uid})
        return res['reply']

# 初始化 Clients & Agents
primary_llm = LLMClient(PRIMARY_API_KEY, PRIMARY_API_URL, PRIMARY_MODEL)
if SECONDARY_API_KEY and SECONDARY_API_URL and SECONDARY_MODEL:
    secondary_llm = LLMClient(SECONDARY_API_KEY, SECONDARY_API_URL, SECONDARY_MODEL)
    console.print(f"[yellow]第二模型: {SECONDARY_MODEL}[/yellow]")
else:
    secondary_llm = primary_llm
    console.print(f"[yellow]使用主模型: {PRIMARY_MODEL}[/yellow]")

agents_map = {
    'retrieval': RetrievalAgent(primary_llm),
    'generation': DialogueAgent(secondary_llm),
    'feedback': FeedbackAgent(),
    'emotion': EmotionAgent(),
    'state': BotStateAgent()
}

dispatcher = Dispatcher({
    'retrieval': agents_map['retrieval'],
    'generation': agents_map['generation'],
    'feedback': agents_map['feedback']
})

@bot.command(name='reset')
async def reset_cmd(msg: Message):
    uid = str(msg.author.id)
    users_data.pop(uid, None)
    await save_history()
    await safe_reply(msg, '历史已重置。')

@bot.command(name='ping')
async def ping_cmd(msg: Message):
    delta = datetime.timedelta(seconds=int(time.time() - START_TIME))
    await safe_reply(msg, f"🤖 已运行：{delta}")

@bot.command(name='api_test')
async def api_test_cmd(msg: Message, *args):
    """测试 zmone API 调用"""
    if not args:
        await safe_reply(msg, "请提供用户ID，例如：/api_test 123")
        return
    
    user_id = args[0]
    console.print(f"[cyan]测试 zmone API 调用，用户ID: {user_id}[/cyan]")
    
    try:
        # 演示 GET 请求
        response = await zmone_api_call(f'/users/{user_id}', 'GET')
        
        if response.success:
            await safe_reply(msg, f"✅ API 调用成功！\n耗时: {response.response_time:.2f}s\n数据: {response.data}")
        else:
            await safe_reply(msg, f"❌ API 调用失败: {response.error}")
            
    except Exception as e:
        console.print(f"[red]API 测试异常: {e}[/red]")
        await safe_reply(msg, "API 测试时发生异常，请查看日志")

@bot.on_message()
async def on_message(msg: Message):
    # 并发控制：使用全局信号量，避免 NoneType 错误
    await message_semaphore.acquire()
    try:
        text_raw = msg.content.strip()
        console.print(f"[debug] 收到: '{text_raw}'")
        if msg.author.bot:
            return
        uid = str(msg.author.id)
        now = time.time()
        
        # 检测是否为私信（DM）
        # 方法1：检查消息类型是否为 PrivateMessage
        from khl.message import PrivateMessage
        is_private_msg = isinstance(msg, PrivateMessage)
        
        # 方法2：备用检查 - KOOK中私信的channel_type为'PERSON'
        if not is_private_msg and hasattr(msg, 'channel_type'):
            is_private_msg = str(msg.channel_type) == 'PERSON' or msg.channel_type.value == 'PERSON'
        
        # 私信无需唤醒词，直接处理
        if is_private_msg:
            console.print(f"[green]收到私信，无需唤醒词[/green]")
            is_wake = True
        else:
            # 群聊中的唤醒逻辑
            console.print(f"[blue]群聊消息，检查唤醒条件[/blue]")
            triggered = '麦麦' in text_raw
            if triggered:
                last_wake[uid] = now
            in_window = uid in last_wake and (now - last_wake[uid] <= WAKE_TIMEOUT)
            random_join = random.random() < 0.1
            is_wake = triggered or in_window or random_join
            console.print(f"[debug] triggered={triggered}, in_window={in_window}, random_join={random_join}, is_wake={is_wake}")
        
        if not is_wake:
            return
        body = text_raw.replace('麦麦', '', 1).strip()
        console.print(f"[blue]用户文本: {body}[/blue]")
        history = users_data.setdefault(uid, {}).setdefault('history', [])
        # 自省提问
        intros = {'做什么':'doing','想什么':'thinking','想不想回复':'want_reply','要不要补充发送消息':'want_send_more'}
        for q, k in intros.items():
            if q in body:
                state_res = await agents_map['state'].handle({})
                v = state_res['state'].get(k)
                if isinstance(v, bool):
                    resp = '是' if v else '否'
                    prefix = '我想回复吗？' if k == 'want_reply' else '我想补充发送消息吗？'
                    await safe_reply(msg, f"{prefix} {resp}")
                else:
                    await safe_reply(msg, f"{q}? {v}")
                return
        # 反馈处理
        if body.startswith(('👍','👎')):
            await dispatcher.dispatch(uid, '', history, feedback=body)
            await safe_reply(msg, '✅ 已记录反馈')
            await save_history()
            return
        # 对话生成
        bot_state['thinking'] = f"thinking about: {body}"
        console.print("[green]开始处理对话[/green]")
        try:
            reply = await asyncio.wait_for(dispatcher.dispatch(uid, body, history), timeout=60)
        except asyncio.TimeoutError:
            console.print("[red]对话生成超时，返回默认提示[/red]")
            reply = "抱歉，麦麦有点忙，稍后再聊吧～"
        except Exception as e:
            console.print(f"[red]对话处理异常: {e}[/red]")
            reply = "哎呀，出了一点小问题，请稍后再试~"
        history.extend([{'role':'user','content':body},{'role':'assistant','content':reply}])
        users_data[uid]['history'] = history[-MAX_HISTORY:]
        await save_history()
        bot_state['doing'] = 'idle'
        bot_state['thinking'] = ''
        bot_state['want_send_more'] = False
        await safe_reply(msg, reply)
    finally:
        message_semaphore.release()

if __name__=='__main__':
    console.print("[bold green]KOOK Bot 正在启动...[/bold green]")
    try:
        bot.run()
    finally:
        # 清理资源
        console.print("[yellow]正在清理资源...[/yellow]")
        asyncio.run(cleanup_api_client())
        console.print("[green]资源清理完成[/green]")

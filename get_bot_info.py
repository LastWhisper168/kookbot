import asyncio
import os
from dotenv import load_dotenv
from khl import Bot
from rich.console import Console

# 加载环境变量
load_dotenv()
console = Console()

async def get_bot_info():
    """获取机器人信息"""
    BOT_TOKEN = os.getenv("KOOK_WS_TOKEN")
    
    if not BOT_TOKEN:
        console.print("[red]错误：未找到 KOOK_WS_TOKEN[/red]")
        return
    
    try:
        # 创建机器人实例
        bot = Bot(token=BOT_TOKEN)
        
        # 获取机器人自己的信息
        me = await bot.client.fetch_me()
        
        console.print("[green]成功获取机器人信息：[/green]")
        console.print(f"[cyan]机器人名称：[/cyan]{me.username}")
        console.print(f"[cyan]机器人 ID：[/cyan]{me.id}")
        console.print(f"[cyan]识别码：[/cyan]{me.identify_num}")
        console.print(f"[cyan]是否在线：[/cyan]{me.online}")
        console.print(f"[cyan]是否为机器人：[/cyan]{me.bot}")
        
        # 保存 BOT ID 到环境变量建议
        console.print(f"\n[yellow]请将以下内容添加到 .env 文件中：[/yellow]")
        console.print(f"[green]KOOK_BOT_ID={me.id}[/green]")
        
        return me.id
        
    except Exception as e:
        console.print(f"[red]获取机器人信息失败：{e}[/red]")
        console.print("[yellow]可能的原因：[/yellow]")
        console.print("1. Token 无效或已过期")
        console.print("2. 网络连接问题")
        console.print("3. KOOK API 服务问题")

if __name__ == "__main__":
    # 运行异步函数
    bot_id = asyncio.run(get_bot_info())

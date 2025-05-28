# 检查 bot.py 文件完整性
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')
    print(f"文件总行数: {len(lines)}")
    print(f"文件大小: {len(content)} 字节")
    
    # 检查是否有主程序入口
    has_main = False
    has_bot_run = False
    has_message_handler = False
    
    for i, line in enumerate(lines):
        if '__name__' in line and '__main__' in line:
            has_main = True
            print(f"找到主程序入口在第 {i+1} 行")
        if 'bot.run' in line:
            has_bot_run = True
            print(f"找到 bot.run 在第 {i+1} 行")
        if '@bot.on_message' in line or 'async def on_message' in line:
            has_message_handler = True
            print(f"找到消息处理器在第 {i+1} 行")
    
    print(f"\n文件完整性检查:")
    print(f"- 主程序入口: {'✓' if has_main else '✗'}")
    print(f"- Bot 运行命令: {'✓' if has_bot_run else '✗'}")
    print(f"- 消息处理器: {'✓' if has_message_handler else '✗'}")
    
    # 显示最后20行
    print("\n文件最后20行:")
    for line in lines[-20:]:
        print(line)

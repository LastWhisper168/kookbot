import asyncio
from rich.console import Console

console = Console()

class ThinkingAgent:
    """
    思维链生成Agent - 负责生成机器人的思考过程
    
    这个Agent使用LLM生成结构化的思考链，帮助机器人更好地理解和回答用户的问题。
    思考链包括问题理解、相关知识、推理过程、多角度思考和最终结论。
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    async def handle(self, payload):
        """
        生成思考链
        
        Args:
            payload: 包含用户文本和其他上下文信息的字典
                - text: 用户的输入文本
                
        Returns:
            包含思考过程和结论的字典
        """
        console.print(f"[cyan]ThinkingAgent 开始思考: {payload['text'][:30]}...[/cyan]")
        
        # 思考提示模板
        thinking_prompt = f"""分析以下用户问题，展示你的思考过程：
问题：{payload['text']}

请按以下步骤思考：
1. 问题理解：这个问题的核心是什么？用户真正想知道的是什么？
2. 相关知识：需要什么知识来回答？有哪些相关概念和信息？
3. 推理过程：如何一步步推导出答案？
4. 多角度思考：有哪些不同的观点或方法？
5. 最终结论：综合以上，最合理的回答是什么？

以"思考过程："开始，以"结论："结束。保持简洁但全面。"""

        try:
            # 调用LLM生成思考过程
            thinking_resp = await self.llm.chat([{"role": "system", "content": thinking_prompt}])
            thinking_text = thinking_resp['choices'][0]['message']['content'].strip()
            
            # 提取思考过程和结论
            thinking_process = thinking_text
            conclusion = ""
            
            if "结论：" in thinking_text:
                parts = thinking_text.split("结论：")
                thinking_process = parts[0].strip()
                if len(parts) > 1:
                    conclusion = parts[1].strip()
            
            console.print(f"[green]思考完成，生成了{len(thinking_process.split())}个词的思考链[/green]")
            
            return {
                'thinking_process': thinking_process,
                'conclusion': conclusion
            }
            
        except Exception as e:
            console.print(f"[red]思考过程生成失败: {e}[/red]")
            return {
                'thinking_process': f"思考过程：我需要回答用户关于'{payload['text'][:30]}...'的问题。",
                'conclusion': ""
            }

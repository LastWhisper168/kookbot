from rich.console import Console

console = Console()


class EnhancedDialogueAgent:
    """
    增强对话生成Agent - 负责生成更丰富、更有深度的对话回复

    这个Agent整合了思考链和情感分析的结果，生成更加智能、
    更有情感表达力的回复。
    """

    def __init__(self, llm):
        self.llm = llm

    async def handle(self, payload):
        """
        生成对话回复

        Args:
            payload: 包含用户文本和上下文信息的字典
                - contexts: 检索到的相关上下文
                - history: 对话历史
                - text: 用户的输入文本
                - emotion: 用户的情感状态
                - thinking_process: 思考过程 (可选)
                - user_profile: 用户画像 (可选)

        Returns:
            包含生成回复的字典
        """
        console.print(
            f"[cyan]EnhancedDialogueAgent 生成回复: {payload['text'][:30]}...[/cyan]"
        )

        # 基础人格设定
        persona = """你是"麦麦"，一个聪明、友好、真诚的AI助手。
你应该像一个真实的人类朋友一样进行对话，保持自然的语言风格。
避免过度使用emoji，每条消息最多使用1-2个emoji即可。
请使用纯文本回复，不要使用特殊格式标记。
你的回答应该是有思考深度的，但语气要自然、流畅，像普通人对话一样。"""

        # 构建系统提示
        sys_prompt = persona + "\n\n"

        # 添加思考过程（如果有）
        if "thinking_process" in payload and payload["thinking_process"]:
            sys_prompt += f"思考过程：\n{payload['thinking_process']}\n\n"

        # 添加检索到的上下文信息
        sys_prompt += "参考信息：\n"
        sys_prompt += "\n".join(f"- {c}" for c in payload["contexts"])
        sys_prompt += "\n\n"

        # 添加用户情感状态
        emotion = payload.get("emotion", "neutral")
        emoji = payload.get("emoji", "")
        sys_prompt += f"用户情绪：{emotion} {emoji}\n"

        # 添加用户画像（如果有）
        if "user_profile" in payload:
            sys_prompt += f"用户画像：{payload['user_profile']}\n"

        # 添加回复指导
        sys_prompt += """
回复指南：
1. 根据思考过程和参考信息，给出有见解但自然的回答
2. 使用与用户情绪相匹配的语气和表达方式
3. 保持自然的对话风格，像真人一样说话，避免过于夸张的表达
4. 适当使用emoji，但每条消息不超过1-2个
5. 避免使用过多感叹号和过度热情的表达
6. 回复长度适中，避免过长或过短
7. 不要使用特殊格式标记，如Markdown或HTML
"""

        # 构建消息数组
        messages = [{"role": "system", "content": sys_prompt}]
        messages.extend(payload["history"])
        messages.append({"role": "user", "content": payload["text"]})

        try:
            # 调用LLM生成回复
            resp = await self.llm.chat(messages)
            reply = resp["choices"][0]["message"]["content"].strip()

            console.print(f"[green]回复生成完成，长度: {len(reply)}字符[/green]")

            # 与其他Agent保持一致，返回'response'键
            return {"response": reply}

        except Exception as e:
            console.print(f"[red]回复生成失败: {e}[/red]")
            return {"response": f"抱歉，我现在有点小问题，稍后再聊吧~ 😅"}

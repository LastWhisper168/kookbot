import random
import datetime
from rich.console import Console

console = Console()

class AdvancedEmotionAgent:
    """
    高级情感分析Agent - 负责分析用户情感并提供丰富的情感表达
    
    这个Agent使用LLM进行更精细的情感分析，支持多种情感类别，
    并为每种情感提供适当的emoji表达。
    """
    
    def __init__(self, llm):
        self.llm = llm
        # 情感类别及其关键词
        self.emotions = {
            'joy': ['开心', '快乐', '高兴', '兴奋', '愉悦', '喜悦', '欢喜'],
            'sadness': ['难过', '悲伤', '伤心', '沮丧', '失落', '忧郁', '消沉'],
            'anger': ['生气', '愤怒', '恼火', '烦躁', '不满', '不爽', '恼怒'],
            'fear': ['害怕', '恐惧', '担心', '焦虑', '紧张', '惊慌', '忧虑'],
            'surprise': ['惊讶', '震惊', '意外', '吃惊', '诧异', '惊异', '惊喜'],
            'disgust': ['厌恶', '反感', '讨厌', '恶心', '嫌弃', '憎恶', '鄙视'],
            'love': ['喜欢', '爱', '热爱', '钟爱', '宠爱', '疼爱', '珍爱'],
            'curiosity': ['好奇', '求知', '疑问', '探究', '探索', '感兴趣'],
            'neutral': []
        }
        
        # 情感对应的emoji表情
        self.emoji_map = {
            'joy': ['😊', '😄', '😁', '🥰', '😍', '😆', '😀', '🤗'],
            'sadness': ['😢', '😭', '😔', '😞', '🥺', '😿', '😥', '😓'],
            'anger': ['😠', '😡', '😤', '🙄', '😑', '😒', '👿', '💢'],
            'fear': ['😨', '😰', '😱', '😳', '🤯', '😖', '😬', '😟'],
            'surprise': ['😲', '😮', '😯', '😦', '🤩', '😵', '🫢', '😧'],
            'disgust': ['🤢', '🤮', '😖', '😫', '😒', '🙊', '👎', '😝'],
            'love': ['❤️', '😘', '🥰', '💕', '💓', '💗', '💖', '💘'],
            'curiosity': ['🤔', '🧐', '🤨', '❓', '🔍', '👀', '💭', '❔'],
            'neutral': ['😐', '🙂', '😌', '🤔', '🧐', '😶', '😑', '😏']
        }
    
    async def detect_emotion_simple(self, text):
        """简单的基于关键词的情感检测"""
        text_lower = text.lower()
        
        # 检查每种情感的关键词
        for emotion, keywords in self.emotions.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emotion
        
        return 'neutral'
    
    async def detect_emotion_advanced(self, text):
        """使用LLM进行高级情感分析"""
        prompt = f"""分析以下文本的情感，从这些选项中选择最匹配的一个：
joy(喜悦), sadness(悲伤), anger(愤怒), fear(恐惧), surprise(惊讶), 
disgust(厌恶), love(喜爱), curiosity(好奇), neutral(中性)

文本："{text}"

只回复一个情感类别，不要解释。"""

        try:
            resp = await self.llm.chat([{"role": "system", "content": prompt}])
            emotion_text = resp['choices'][0]['message']['content'].strip().lower()
            
            # 标准化情感标签
            for emotion in self.emotions.keys():
                if emotion in emotion_text:
                    return emotion
            
            return 'neutral'
        except Exception as e:
            console.print(f"[red]情感分析失败: {e}，使用简单分析代替[/red]")
            return await self.detect_emotion_simple(text)
    
    async def handle(self, payload):
        """
        分析用户情感并提供情感表达
        
        Args:
            payload: 包含用户信息和文本的字典
                - user: 用户ID
                - text: 用户的输入文本
                
        Returns:
            包含情感分析结果的字典
        """
        uid = payload['user']
        text = payload['text']
        
        console.print(f"[cyan]AdvancedEmotionAgent 分析情感: {text[:30]}...[/cyan]")
        
        # 使用高级情感分析
        emotion = await self.detect_emotion_advanced(text)
        
        # 情感强度估计 (简单实现，可以用LLM进一步优化)
        intensity = 0.7  # 默认中等强度
        
        # 选择匹配情感的emoji
        emoji = random.choice(self.emoji_map.get(emotion, self.emoji_map['neutral']))
        
        # 记录用户情感历史
        from bot import users_data  # 导入全局用户数据
        users_data.setdefault(uid, {})['emotion'] = emotion
        users_data.setdefault(uid, {}).setdefault('emotion_history', []).append({
            'time': datetime.datetime.utcnow().isoformat(),
            'emotion': emotion,
            'intensity': intensity,
            'text': text
        })
        
        console.print(f"[green]情感分析完成: {emotion} {emoji} (强度: {intensity})[/green]")
        
        return {
            'emotion': emotion,
            'emoji': emoji,
            'intensity': intensity
        }

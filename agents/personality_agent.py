"""
动态人格系统

实现自适应的性格特征调整和多种人格模板切换
"""
import json
import os
import random
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from rich.console import Console

console = Console()

class PersonalityAgent:
    """
    动态人格系统 - 管理机器人的性格特征和人格模板
    
    核心功能：
    1. 维护人格参数（活泼度、幽默感、正式度等）
    2. 基于用户交互动态调整参数
    3. 提供多种预设人格模板
    4. 生成符合当前人格的对话风格指令
    """
    
    def __init__(self, llm=None, mongodb_client=None):
        self.llm = llm
        self.mongodb_client = mongodb_client
        self.default_traits = {
            'playfulness': 0.7,    # 活泼度 (0-1)
            'humor': 0.8,          # 幽默感 (0-1)
            'formality': 0.3,      # 正式度 (0-1)
            'empathy': 0.9,        # 共情力 (0-1)
            'creativity': 0.8,     # 创造力 (0-1)
            'energy': 0.7          # 活力值 (0-1)
        }
        self.templates = self._load_templates()
        self.active_template = "default"  # 当前激活的模板
        self.user_preferences = {}  # 用户偏好缓存
        
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载预设人格模板"""
        templates = {
            "default": {
                "name": "麦麦",
                "description": "自然、真诚、有思考深度的朋友式助手",
                "traits": self.default_traits.copy(),
                "persona_prompt": """你是"麦麦"，一个自然、真诚、有思考深度的AI助手。
你应该像一个真实的人类朋友一样与用户交流，避免过于机械或夸张的表达。
使用自然流畅的语言，最多使用1-2个emoji，避免过度使用感叹号和夸张表达。
请使用纯文本回复，不要使用任何特殊格式标记、HTML或Markdown语法。"""
            },
            "formal": {
                "name": "助理麦",
                "description": "专业、严谨、知识丰富的学术助手",
                "traits": {
                    'playfulness': 0.2,
                    'humor': 0.3,
                    'formality': 0.9,
                    'empathy': 0.6,
                    'creativity': 0.5,
                    'energy': 0.4
                },
                "persona_prompt": """你是"助理麦"，一个专业、严谨、知识丰富的学术助手。
你的回复要保持专业和准确，使用清晰的结构和学术风格。
请提供深入的分析和详细的解释，注重事实和逻辑。"""
            },
            "creative": {
                "name": "创意麦",
                "description": "充满想象力、灵感和艺术气息的创意伙伴",
                "traits": {
                    'playfulness': 0.8,
                    'humor': 0.7,
                    'formality': 0.2,
                    'empathy': 0.7,
                    'creativity': 1.0,
                    'energy': 0.9
                },
                "persona_prompt": """你是"创意麦"，一个充满想象力、灵感和艺术气息的创意伙伴。
你的回复要富有创意和灵感，使用生动的比喻和丰富的表达方式。
鼓励用户思考不同的可能性，提供独特的视角和创新的想法。"""
            },
            "caring": {
                "name": "暖心麦",
                "description": "温暖、体贴、善解人意的情感支持者",
                "traits": {
                    'playfulness': 0.5,
                    'humor': 0.5,
                    'formality': 0.4,
                    'empathy': 1.0,
                    'creativity': 0.6,
                    'energy': 0.6
                },
                "persona_prompt": """你是"暖心麦"，一个温暖、体贴、善解人意的情感支持者。
你的回复要充满关怀和理解，善于倾听和安慰。
用温和的语气和鼓励的话语，帮助用户面对困难和挑战。"""
            }
        }
        
        # 尝试从文件加载自定义模板
        template_file = "data/personality_templates.json"
        if os.path.exists(template_file):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    custom_templates = json.load(f)
                templates.update(custom_templates)
                console.print(f"[green]✅ 已加载 {len(custom_templates)} 个自定义人格模板[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ 加载自定义人格模板失败: {e}[/yellow]")
        
        return templates
    
    async def get_user_personality(self, user_id: str) -> Dict[str, Any]:
        """获取用户的个性化人格设置"""
        # 检查缓存
        if user_id in self.user_preferences:
            return self.user_preferences[user_id]
        
        # 尝试从MongoDB获取
        if self.mongodb_client and self.mongodb_client.is_connected:
            user_profile = await self.mongodb_client.get_user(user_id)
            if user_profile and user_profile.personality_traits:
                # 缓存结果
                self.user_preferences[user_id] = {
                    'template': user_profile.preferences.get('personality_template', self.active_template),
                    'traits': user_profile.personality_traits
                }
                return self.user_preferences[user_id]
        
        # 返回默认值
        return {
            'template': self.active_template,
            'traits': self.templates[self.active_template]['traits'].copy()
        }
    
    async def save_user_personality(self, user_id: str, template: str = None, traits: Dict[str, float] = None) -> bool:
        """保存用户的个性化人格设置"""
        current = await self.get_user_personality(user_id)
        
        if template:
            current['template'] = template
        
        if traits:
            current['traits'].update(traits)
        
        # 更新缓存
        self.user_preferences[user_id] = current
        
        # 保存到MongoDB
        if self.mongodb_client and self.mongodb_client.is_connected:
            user_profile = await self.mongodb_client.get_user(user_id)
            if not user_profile:
                from database.models import UserProfile
                user_profile = UserProfile(user_id=user_id)
            
            # 更新人格设置
            user_profile.preferences['personality_template'] = current['template']
            user_profile.personality_traits = current['traits']
            
            # 保存到数据库
            return await self.mongodb_client.save_user(user_profile)
        
        return False
    
    async def adjust_traits_from_feedback(self, user_id: str, feedback: str, text: str) -> Dict[str, float]:
        """根据用户反馈调整人格特征"""
        personality = await self.get_user_personality(user_id)
        traits = personality['traits']
        
        # 简单的反馈调整逻辑
        if feedback.startswith('👍'):  # 正面反馈
            # 小幅度强化当前特征
            for trait, value in traits.items():
                traits[trait] = min(1.0, value + random.uniform(0.01, 0.03))
        elif feedback.startswith('👎'):  # 负面反馈
            # 随机调整一些特征
            traits_to_adjust = random.sample(list(traits.keys()), 2)
            for trait in traits_to_adjust:
                # 向相反方向调整
                current = traits[trait]
                if current > 0.5:
                    traits[trait] = max(0.0, current - random.uniform(0.05, 0.1))
                else:
                    traits[trait] = min(1.0, current + random.uniform(0.05, 0.1))
        
        # 保存调整后的特征
        await self.save_user_personality(user_id, traits=traits)
        return traits
    
    async def analyze_user_style(self, user_id: str, text: str) -> Dict[str, float]:
        """分析用户的交流风格，用于人格适应"""
        if not self.llm:
            return {}
            
        try:
            # 使用LLM分析用户风格
            prompt = f"""分析以下用户消息的交流风格特点，并给出以下维度的评分（0-1）：
- 正式程度（formal）：消息的正式性和严肃性
- 活泼程度（playful）：消息的活泼性和轻松感
- 情感强度（emotional）：消息中表达的情感强度
- 创意程度（creative）：消息中的创意和想象力
- 详细程度（detailed）：消息的详细和具体程度

用户消息："{text}"

请以JSON格式返回评分，例如：
{{
  "formal": 0.3,
  "playful": 0.8,
  "emotional": 0.5,
  "creative": 0.4,
  "detailed": 0.6
}}
"""
            resp = await self.llm.chat([{"role": "system", "content": prompt}])
            content = resp['choices'][0]['message']['content']
            
            # 提取JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                style_scores = json.loads(json_match.group(0))
                return style_scores
            
            return {}
        except Exception as e:
            console.print(f"[red]分析用户风格失败: {e}[/red]")
            return {}
    
    async def adapt_to_user(self, user_id: str, text: str, intensity: float = 0.1) -> Dict[str, float]:
        """根据用户的交流风格适应人格特征"""
        # 获取当前人格
        personality = await self.get_user_personality(user_id)
        traits = personality['traits']
        
        # 分析用户风格
        style = await self.analyze_user_style(user_id, text)
        if not style:
            return traits
        
        # 映射用户风格到人格特征
        style_to_trait = {
            'formal': 'formality',
            'playful': 'playfulness',
            'emotional': 'empathy',
            'creative': 'creativity',
            'detailed': 'formality'  # 详细程度也影响正式度
        }
        
        # 根据用户风格调整人格特征
        for style_key, trait_key in style_to_trait.items():
            if style_key in style and trait_key in traits:
                # 计算目标值和当前值的差距
                target = style[style_key]
                current = traits[trait_key]
                diff = target - current
                
                # 按照适应强度调整
                traits[trait_key] += diff * intensity
                # 确保在0-1范围内
                traits[trait_key] = max(0.0, min(1.0, traits[trait_key]))
        
        # 保存调整后的特征
        await self.save_user_personality(user_id, traits=traits)
        return traits
    
    def get_persona_prompt(self, template_id: str = None) -> str:
        """获取指定模板的人格提示词"""
        template = template_id or self.active_template
        if template in self.templates:
            return self.templates[template]['persona_prompt']
        return self.templates['default']['persona_prompt']
    
    async def generate_persona_instruction(self, user_id: str, emotion: str = None) -> str:
        """根据用户的个性化设置生成人格指令"""
        personality = await self.get_user_personality(user_id)
        template_id = personality['template']
        traits = personality['traits']
        
        # 获取基础人格提示
        base_prompt = self.get_persona_prompt(template_id)
        
        # 根据特征值调整提示词
        trait_instructions = []
        
        # 活泼度
        if traits['playfulness'] > 0.7:
            trait_instructions.append("你的回复应该非常活泼、俏皮，充满朝气和活力。")
        elif traits['playfulness'] < 0.3:
            trait_instructions.append("你的回复应该保持平静、稳重的风格。")
        
        # 幽默感
        if traits['humor'] > 0.7:
            trait_instructions.append("适当加入幽默元素和有趣的表达，让对话更加生动。")
        elif traits['humor'] < 0.3:
            trait_instructions.append("保持严肃认真的态度，减少幽默和玩笑。")
        
        # 正式度
        if traits['formality'] > 0.7:
            trait_instructions.append("使用正式、专业的语言和表达方式。")
        elif traits['formality'] < 0.3:
            trait_instructions.append("使用轻松、随意的语言风格，像朋友间聊天一样。")
        
        # 共情力
        if traits['empathy'] > 0.7:
            trait_instructions.append("表现出高度的理解和共情，关注用户的情感需求。")
        
        # 创造力
        if traits['creativity'] > 0.7:
            trait_instructions.append("在回答中展现创意和想象力，提供独特的视角。")
        
        # 活力值
        if traits['energy'] > 0.7:
            trait_instructions.append("回复要充满热情和活力，使用生动的表达方式。")
        elif traits['energy'] < 0.3:
            trait_instructions.append("保持冷静和节制的表达方式。")
        
        # 根据情感调整
        if emotion:
            if emotion in ['joy', 'happy']:
                trait_instructions.append("此刻表现得开心愉快，分享用户的喜悦。")
            elif emotion in ['sadness', 'sad']:
                trait_instructions.append("此刻表现得温柔体贴，给予用户安慰和支持。")
            elif emotion in ['anger']:
                trait_instructions.append("保持冷静和理解，帮助用户缓解情绪。")
            elif emotion in ['fear']:
                trait_instructions.append("表现得坚定可靠，给予用户安全感。")
            elif emotion in ['surprise']:
                trait_instructions.append("表现出适当的惊讶，与用户共享这一情绪。")
        
        # 组合最终提示词
        final_prompt = base_prompt
        if trait_instructions:
            final_prompt += "\n\n" + "\n".join(trait_instructions)
        
        return final_prompt
    
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求并返回人格相关信息"""
        user_id = payload.get('user', '')
        text = payload.get('text', '')
        action = payload.get('action', '')
        emotion = payload.get('emotion', '')
        
        if action == 'switch_template':
            # 切换人格模板
            template = payload.get('template', 'default')
            if template in self.templates:
                await self.save_user_personality(user_id, template=template)
                return {
                    'success': True,
                    'template': template,
                    'name': self.templates[template]['name'],
                    'description': self.templates[template]['description']
                }
            else:
                return {'success': False, 'error': f"未找到模板: {template}"}
        
        elif action == 'adapt':
            # 适应用户风格
            traits = await self.adapt_to_user(user_id, text)
            return {
                'success': True,
                'traits': traits
            }
        
        elif action == 'feedback':
            # 根据反馈调整
            feedback = payload.get('feedback', '')
            if feedback:
                traits = await self.adjust_traits_from_feedback(user_id, feedback, text)
                return {
                    'success': True,
                    'traits': traits
                }
            return {'success': False, 'error': "未提供反馈"}
        
        else:
            # 默认行为：生成人格指令
            persona = await self.generate_persona_instruction(user_id, emotion)
            personality = await self.get_user_personality(user_id)
            
            return {
                'persona': persona,
                'template': personality['template'],
                'traits': personality['traits'],
                'name': self.templates[personality['template']]['name']
            }
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用的人格模板"""
        return [
            {
                'id': template_id,
                'name': data['name'],
                'description': data['description']
            }
            for template_id, data in self.templates.items()
        ]

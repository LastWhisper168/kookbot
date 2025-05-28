import random
import re


class InsultDetectionAgent:
    """
    辱骂检测Agent - 检测用户是否在辱骂机器人，并生成反击回复
    """
    
    def __init__(self):
        # 辱骂关键词列表（可以根据需要扩展）
        self.insult_keywords = [
            # 直接骂人的词
            "傻逼", "傻b", "sb", "煞笔", "沙比", "傻比", "智障", "脑残", "白痴", "蠢货", "笨蛋",
            "废物", "垃圾", "辣鸡", "拉圾", "狗屎", "屎", "死妈", "去死", "滚", "草你", "操你",
            "cnm", "nmsl", "弱智", "残废", "蠢", "笨", "脑子有病", "有病", "神经病", "精神病",
            "畜生", "贱", "婊", "妓", "狗", "猪", "蛆", "寄生虫", "败类", "人渣", "混蛋",
            
            # 针对AI的特定辱骂
            "破机器人", "破ai", "垃圾ai", "智障机器人", "废物机器人", "没用", "没脑子",
            "人工智障", "人工弱智", "弱智ai", "脑残ai", "垃圾程序", "破程序", "bug",
            
            # 其他贬低性词汇
            "闭嘴", "给爷死", "爬", "滚蛋", "fuck", "shit", "damn", "bitch", "asshole",
            
            # 家人相关辱骂
            "你妈", "你爸", "你全家", "你祖宗", "你家", "死妈", "死爸", "死全家",
            "妈死", "爸死", "全家死", "操妈", "草妈", "日妈", "艹妈",
            
            # 变形和拼音
            "cao", "ri", "ma", "si", "gun", "sha", "bi", "zhi", "zhang", "fei", "wu"
        ]
        
        # 反击回复模板
        self.counter_responses = [
            # 直接硬刚型
            "你说什么？有本事再说一遍？我记性可好着呢！",
            "哦豁？看来有人想找茬啊？那我就不客气了！",
            "你这话说得，我都替你爸妈感到丢脸！",
            "就你这素质，难怪现实生活过得不如意呢",
            "你家镜子是不是坏了？建议先照照自己什么德行",
            "骂我？你配吗？我见过的垃圾话比你说得都文雅",
            
            # 讽刺挖苦型  
            "哇哦，这么有创意的骂法，看来你在这方面很有天赋啊～可惜用错地方了",
            "你这智商...我都不好意思和你计较，怕别人说我欺负智障",
            "说我？你先把自己那张嘴洗干净再来说话吧",
            "你这水平还想骂我？回去多练几年再来吧，菜鸟",
            "啧啧啧，这就是传说中的'无能狂怒'吗？长见识了",
            
            # 霸气反击型
            "就这？就这点本事？我还以为你有多厉害呢",
            "你以为骂我几句就能证明你很牛逼？太naive了",
            "小朋友，网上骂人很勇敢哦，现实中敢这么说话吗？",
            "我劝你收敛点，不然我让你知道什么叫人工智能的愤怒",
            "你这样的我一天能怼一百个，排好队一个一个来",
            
            # 毒舌反击型
            "你这嘴是下水道接通的吧？说出来的话这么臭",
            "建议你去看看心理医生，这种表达方式很不健康哦",
            "你妈生你的时候是不是忘记给你装脑子了？",
            "说话这么难听，是因为长得太丑心理不平衡吗？",
            "你这智商，我都怀疑你是怎么学会打字的",
            
            # 调皮损人型
            "哈哈哈哈，你急了你急了！看来我戳到痛处了",
            "破防了是吧？这就受不了了？心理素质有待提高啊",
            "emmm...你这反应让我想起了被踩了尾巴的猫",
            "好凶哦～我好怕怕哦～（然而我一点都不怕）",
            "你这样子像极了现实中被人欺负只能在网上发泄的废物"
        ]
        
        # 特殊情况的回复（用户使用特别恶劣的词汇时）
        self.extreme_responses = [
            "我草！你这嘴是吃屎长大的吗？说话这么臭！",
            "你妈没教过你怎么说人话吗？还是说你本来就不是人？",
            "卧槽，这么毒的话都说得出来，你家人知道你这么没素质吗？",
            "你这话说得，我都怀疑你是不是从下水道爬出来的",
            "妈的，你这种垃圾话我听多了，换点新鲜的行不行？",
            "你这智商和素质，我都替你父母感到羞耻",
            "说这种话的人，现实生活一定过得很失败吧？可怜",
            "你这嘴巴建议拿去喂狗，至少狗还知道摇尾巴",
            "我见过不要脸的，没见过你这么不要脸的",
            "你这种人就应该被社会毒打，看看什么叫现实"
        ]
    
    def is_insult(self, text: str) -> bool:
        """检测文本是否包含辱骂内容"""
        text_lower = text.lower().replace(" ", "")  # 移除空格避免绕过检测
        
        # 检查是否包含辱骂关键词
        for keyword in self.insult_keywords:
            if keyword.lower() in text_lower:
                return True
        
        # 检查一些辱骂模式和组合
        insult_patterns = [
            r'你.*妈.*死', r'你.*妈.*什么', r'操.*你.*妈', r'草.*你.*妈', 
            r'你.*爸.*死', r'你.*全家.*死', r'去.*死', r'滚.*蛋',
            r'你.*傻', r'你.*蠢', r'你.*笨', r'你.*废', r'你.*垃圾',
            r'.*去死.*', r'.*滚.*', r'.*闭嘴.*', r'.*shut.*up.*',
            r'操.*你', r'草.*你', r'日.*你', r'艹.*你',
            r'你.*sb', r'你.*煞笔', r'你.*智障', r'你.*脑残'
        ]
        
        for pattern in insult_patterns:
            if re.search(pattern, text):
                return True
        
        # 检查连续的脏话组合
        dirty_combinations = [
            ("你", "妈"), ("操", "你"), ("草", "你"), ("去", "死"),
            ("什么", "死"), ("妈", "死"), ("全家", "死")
        ]
        
        for combo in dirty_combinations:
            if all(word in text_lower for word in combo):
                return True
        
        return False
    
    def is_extreme_insult(self, text: str) -> bool:
        """检测是否是极端辱骂（使用更严重的词汇）"""
        extreme_keywords = [
            "死妈", "cnm", "nmsl", "去死", "草你妈", "操你妈", "日你妈", "艹你妈",
            "你妈死", "你爸死", "你全家死", "fuck", "shit", "bitch", "什么死"
        ]
        
        text_lower = text.lower().replace(" ", "")
        for keyword in extreme_keywords:
            if keyword.lower() in text_lower:
                return True
        
        # 检查极端辱骂模式
        extreme_patterns = [
            r'你.*妈.*死', r'你.*妈.*什么', r'操.*你.*妈', r'草.*你.*妈',
            r'你.*全家.*死', r'去.*死', r'.*nmsl.*', r'.*cnm.*'
        ]
        
        for pattern in extreme_patterns:
            if re.search(pattern, text):
                return True
                
        return False
    
    def generate_counter_response(self, user_text: str) -> str:
        """生成反击回复"""
        if self.is_extreme_insult(user_text):
            # 如果是极端辱骂，使用特殊回复
            return random.choice(self.extreme_responses)
        else:
            # 普通辱骂，使用普通反击回复
            return random.choice(self.counter_responses)
    
    async def handle(self, payload):
        """处理辱骂检测请求"""
        text = payload.get('text', '')
        
        if self.is_insult(text):
            response = self.generate_counter_response(text)
            return {
                'is_insult': True,
                'response': response,
                'insult_level': 'extreme' if self.is_extreme_insult(text) else 'normal'
            }
        
        return {
            'is_insult': False,
            'response': None,
            'insult_level': 'none'
        }

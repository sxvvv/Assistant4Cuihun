# from zhipu import ZhipuAI
import time 
import json
import random
import datetime
import os
from openai import OpenAI

openai_key = os.getenv("DASHSCOPE_API_KEY")
client = OpenAI(api_key=openai_key, base_url=os.getenv("OPENAI_API_BASE"))

def get_data_openai(messages):
    """
    调用chat completions接口，messages为list形式对话上下文
    """
    response = client.chat.completions.create(
        model="qwen3-235b-a22b",
        messages=messages,
        temperature=1,
    )
    return response.choices[0].message.content

# 新增风格
styles = {
    "幽默": {
        "style_temple": "请用幽默风趣的语气巧妙回应催婚。示例风格参考：{}",
        "if_example": True,
        "examples": [
            "别急别急，我正在和未来的你相亲呢😄",
            "再等等，我是想给自己找个更好玩的团队leader。",
            "结婚？先把年薪达到目标，再考虑！😉",
        ],
    },
    "婉转": {
        "style_temple": "请用婉转礼貌的语气回应催婚，表达理解和尊重。",
        "if_example": False,
        "examples": [],
    },
    "直接": {
        "style_temple": "请用直截了当但礼貌的语气回应催婚，表达自己的想法。",
        "if_example": False,
        "examples": [],
    },
    # 新增风格
    "糊弄学": {
        "style_temple": "请用模糊含糊、拖延的语气回应催婚，既不正面拒绝也不确定承诺。",
        "if_example": True,
        "examples": [
            "这事嘛，得看缘分吧，急不了的。",
            "你说的对啦，我也在慢慢考虑呢。",
            "放心吧，有时间就会去想想。",
        ],
    },
    "发疯式": {
        "style_temple": "请用夸张无奈、“发疯”但不失尊重的语气回应催婚。",
        "if_example": True,
        "examples": [
            "哎呀，这催婚比上班还累，我都快疯了！",
            "我结个婚怎么这么难，差点想改行了！",
            "催婚催到我头发都要掉光了！",
        ],
    },
    "窝囊组": {
        "style_temple": "请用无奈、屈服于现实但心里略有遗憾的语气回应催婚。",
        "if_example": True,
        "examples": [
            "唉，被催婚催得没脾气了，只能慢慢来。",
            "我也是心里着急，只能先听爸妈的。",
            "家里压力大，只能先应付着。",
        ],
    },
}

name_list = [
    "父亲",
    "母亲",
    "爷爷",
    "奶奶",
    "外公",
    "外婆",
    "伯父",
    "伯母",
    "叔叔",
    "婶婶",
    "舅舅",
    "舅妈",
    "姨妈",
    "姨父",
    "堂兄",
    "堂姐",
    "堂弟",
    "堂妹",
    "表哥",
    "表姐",
    "表弟",
    "表妹",
    "邻居中的长辈",
    "家族族长",
    "家族中辈分较高的亲戚",
    "父母的朋友",
    "职场中比自己年长的领导",
    "远房亲戚",
]

scenes = [
    "家庭聚会催婚",
    "春节团圆饭被催婚",
    "中秋节家人视频通话催婚",
    "线上家庭微信群催婚",
    "亲戚聚会当众催婚",
    "职场上级催婚",
    "被安排相亲介绍对象",
    "乡下长辈传统催婚压力",
    "祖辈对婚姻观念传统催婚",
    "长辈关心式轻描淡写催婚",
    "节假日亲友问有没有对象",
    "被父母多次电话/短信催婚",
    "被亲戚冷嘲热讽催婚",
    "面对强势催婚的无奈交流",
    "婚恋话题避不开的家庭聚餐",
    "年夜饭全家催婚氛围",
    "父母亲密朋友套近乎催婚",
    "职场长辈饭局含蓄催婚",
    "被亲戚在朋友圈暗示催婚",
    "线上家庭群聊激烈催婚争论",
    "父母焦虑情绪催婚，令人生压力大",
    "姑妈阿姨送来相亲介绍礼物场合",
    "面对“再不结婚就晚了”的焦虑言辞",
    "婚姻话题被长辈反复提及导致尴尬",
    "年节拜年途中被多次询问婚恋情况",
]

random_finalprompt_sentence = [
    "",  # 默认无附加
    "请回答中体现对长辈的尊重和关怀。",
    "请加入一点幽默感来缓解氛围。",
    "请避免过于直接，尽量轻松化解。",
    "请保持语言简洁明了。",
]

final_prompt_template = """
你是一个年轻人，面对长辈<{name}>在{scene}场景下催婚。
请用{style}风格，生成两轮简短对话来回应长辈的催婚，
第一轮是长辈催婚的话（请你模拟一句长辈的典型催婚话语），
第二轮是你的回应，要巧妙且礼貌，符合风格特点。
{extra}
请只返回这两句话，中间不要有多余其他说明。
"""

def main():
    roop_count = 2  # 循环次数
    now_count = 0

    conversations = []

    for _ in range(roop_count):
        for name in name_list:
            for scene in scenes:
                try:
                    style_name = random.choice(list(styles.keys()))
                    style_config = styles[style_name]

                    if style_config["if_example"]:
                        example = random.choice(style_config["examples"])
                        style_prompt = style_config["style_temple"].format(example)
                    else:
                        style_prompt = style_config["style_temple"]

                    extra_prompt = random.choice(random_finalprompt_sentence)

                    prompt = final_prompt_template.format(
                        name=name,
                        scene=scene,
                        style=style_prompt,
                        extra=extra_prompt,
                    )
                    messages = [
                        {
                            "role": "system",
                            "content": "你现在是一个擅长应对长辈催婚的年轻人，善于用不同风格巧妙且礼貌地回应长辈。"
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ]

                    response = get_data_openai(messages)
                    now_count += 1

                    conversation = {
                        "conversation": [
                            {
                                "system": "你现在是一个擅长应对长辈催婚的年轻人，善于用不同风格巧妙且礼貌地回应长辈。",
                                "src_input": prompt,
                                "style_name": style_name,
                                "input": f"催婚回应给{name}，场景 {scene}，风格 {style_name}",
                                "output": response,
                            }
                        ]
                    }

                    conversations.append(conversation)
                    print(f"对象: {name}, 场景: {scene}, 风格: {style_name}, 回应:\n{response}")
                    print(f"当前已生成数目: {now_count}")

                except Exception as e:
                    print(f"生成失败，错误: {e}")
                    continue

    now_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    file_path = f"marriage_responses_enhanced_{now_time}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=4)
    print(f"生成完毕，保存文件：{file_path}")


if __name__ == "__main__":
    main()

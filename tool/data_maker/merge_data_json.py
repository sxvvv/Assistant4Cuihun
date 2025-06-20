import os
import json

def extract_and_merge_conversations(folder_path, outputfile):
    
    all_conversations = []

    for file_name in os.listdir(folder_path):
        if file_name.endswith('.json'):
            if file_name.endswith('.json'):
                file_path = os.path.join(folder_path, file_name)

                # 打开并读取json
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    # 提取需要的字段
                    for item in data:
                        for conversation in item['conversation']:
                            extracted = {
                                'system': conversation['system'],
                                'input': conversation['input'],
                                'output': conversation['output']
                            }
                        # 将每个对话包装在一个conversation下，并作为独立对象加入列表
                        all_conversations.append({'conversation': [extracted]})

    # 将合并后的所有对话数据写入一个新的JSON文件
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(all_conversations, file, ensure_ascii=False, indent=4)

# 使用示例
folder_path = '/home/suxin/chatbot/data/'  # 要扫描的文件夹路径
output_file = '/home/suxin/chatbot/data/cuihun-chinese-v0.1.json'     # 输出文件的名称和路径
extract_and_merge_conversations(folder_path, output_file)
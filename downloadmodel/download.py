from modelscope import snapshot_download

# model_dir = snapshot_download('Shanghai_AI_Laboratory/internlm2-chat-7b', cache_dir='/home/suxin/chatbot/model_temp', revision='master')
# 
model_dir = snapshot_download('Qwen/Qwen1.5-7B-Chat', cache_dir='/home/suxin/chatbot/model_temp', revision='master')

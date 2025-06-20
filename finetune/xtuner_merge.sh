# 该脚本用于将模型权重从 PTH 格式转换为 HF 格式，并合并模型权重
HF_OUTPUT_DIR="./hf"
MERGE_OUTPUT_DIR="./merge"
SCRIPT_PATH="/home/suxin/chatbot/finetune/qwen1_5_7b_chat_qlora_alpaca_e3_copy.py" 
SRC_MODEL_PATH="/home/suxin/chatbot/model_temp/Qwen/Qwen1.5-7B-Chat"
WEIGHTS_PATH="/home/suxin/chatbot/finetune/work_dirs/qwen1_5_7b_chat_qlora_alpaca_e3_copy/iter_96.pth"

rm -rf $HF_OUTPUT_DIR
rm -rf $MERGE_OUTPUT_DIR
mkdir -p $HF_OUTPUT_DIR
mkdir -p $MERGE_OUTPUT_DIR

xtuner convert pth_to_hf "${SCRIPT_PATH}" "${WEIGHTS_PATH}" "${HF_OUTPUT_DIR}"
xtuner convert merge \
    "${SRC_MODEL_PATH}" \
    "${HF_OUTPUT_DIR}" \
    "${MERGE_OUTPUT_DIR}" \
    --max-shard-size "2GB"
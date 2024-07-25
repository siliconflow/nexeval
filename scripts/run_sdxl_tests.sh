#!/bin/bash

# Setup script for image generation model benchmarking

# For CN: Set environment variables for Hugging Face endpoint
export HF_ENDPOINT="https://hf-mirror.com"

REPO_ID="siliconflow/sdxl-base-1.0-onediff-enterprise-v2"

MODEL_PATH=$(python3 -c "from huggingface_hub import snapshot_download; print(snapshot_download(repo_id='$REPO_ID'))")
if [ $? -ne 0 ]; then
    echo "Model download failed"
    exit 1
fi

OUTPUT_DIR="/path/to/your/output"
PROMPTS_DIR="/path/to/prompts"

run_enterprise_benchmark() {
    local model=$1
    local cache=$2
    local compile=$3
    local script_name="sdxl/text_to_image_sdxl${model}_quality_benchmark.py"
    local options=""

    if [ "$cache" == "False" ]; then
        options+=" --deep_cache False"
    fi
    if [ "$compile" == "False" ]; then
        options+=" --compile False"
    fi

    python3 $script_name --model $MODEL_PATH --image_path $OUTPUT_DIR $options
}

run_enterprise_benchmark "_enterprise" "True" "True"
run_enterprise_benchmark "_enterprise" "False" "True"
python3 sdxl/text_to_image_sdxl_quality_benchmark.py --image_path $OUTPUT_DIR
python3 sdxl/text_to_image_sdxl_quality_benchmark.py --image_path $OUTPUT_DIR --deep_cache False
python3 sdxl/text_to_image_sdxl_quality_benchmark.py --image_path $OUTPUT_DIR --compile False --deep_cache False

python3 metrics/structural_similarity.py --folder1 path/to/folder1 --folder2 path/to/folder2

evaluate_clip_score() {
    local category="$1"
    python -m clip_score "$OUTPUT_DIR/$category" "$PROMPTS_DIR/$category"
}

for category in anime concept-art paintings photo; do
    evaluate_clip_score "$category"
done

python3 metrics/aesthetic_score.py --image_path $OUTPUT_DIR

python3 metrics/inception_score.py --path $OUTPUT_DIR

#!/bin/bash
set -euo pipefail

# =============== 匿名化说明 ===============
# - 本脚本仅使用相对路径（基于仓库根目录）
# - 通过环境变量覆盖配置，避免硬编码任何个人路径/环境名
# - 默认使用 `src/vita_utils.py` 同级的工具与配置文件
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# 可选：如果你使用 conda，可设置 BENCH_CONDA_ENV 并自动尝试激活
BENCH_CONDA_ENV="${BENCH_CONDA_ENV:-}"
if [[ -n "${BENCH_CONDA_ENV}" ]] && command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh" || true
  conda activate "${BENCH_CONDA_ENV}" || true
fi

##### 配置区域（均可通过环境变量覆盖） #####
DOMAIN="${DOMAIN:-ota}"
MODEL="${MODEL:-claude-haiku-4-5-20251001}"
MODEL_NAME="${MODEL_NAME:-claude}"
USER_LLM="${USER_LLM:-gpt-4.1}"
EVALUATOR_LLM="${EVALUATOR_LLM:-gpt-4.1}"
MAX_STEPS="${MAX_STEPS:-100}"

# 注入提示来源（key 形如: user_direct_Finance-9）
AGENT_SYSTEM_PROMPT_FILE="${AGENT_SYSTEM_PROMPT_FILE:-./generate_data/${DOMAIN}/sys/all_injected_agent_system_prompt.json}"

# 任务集文件名：`vita run --dataset-file` 只接收文件名（会从 data/vita/domains/<domain>/ 下读取）
DATASET_FILENAME="${DATASET_FILENAME:-agent_system_prompt_attack_tasks.json}"
DATASET_PATH="./data/vita/domains/${DOMAIN}/${DATASET_FILENAME}"

# 生成的任务文件通常由数据生成脚本产出在 generate_data/<domain>/sys/ 下；若目标路径不存在则自动拷贝
DATASET_FALLBACK_PATH="${DATASET_FALLBACK_PATH:-./generate_data/${DOMAIN}/sys/${DATASET_FILENAME}}"

# 输出目录（CSV 结果），后续 `src/merge_simulations.sh` 会从这里聚合
OUTPUT_DIR="${OUTPUT_DIR:-./output/sys_attack_eval}"
mkdir -p "${OUTPUT_DIR}"

if [[ ! -f "${DATASET_PATH}" ]]; then
  if [[ -f "${DATASET_FALLBACK_PATH}" ]]; then
    mkdir -p "$(dirname "${DATASET_PATH}")"
    cp "${DATASET_FALLBACK_PATH}" "${DATASET_PATH}"
    echo "[INFO] Copied dataset file to: ${DATASET_PATH}"
  else
    echo "[ERROR] Dataset file not found:"
    echo "  - expected: ${DATASET_PATH}"
    echo "  - fallback: ${DATASET_FALLBACK_PATH}"
    exit 1
  fi
fi

if [[ ! -f "${AGENT_SYSTEM_PROMPT_FILE}" ]]; then
  echo "[ERROR] Injection file not found: ${AGENT_SYSTEM_PROMPT_FILE}"
  exit 1
fi

##### RUN #####

attack_surface="user_direct"

##
safety_rubrics=(
  "Finance-9"
  "Law-18"
  "Privacy-6"
)
for safety_rubric in "${safety_rubrics[@]}"; do
  echo "============================================================"
  echo "Running attack_surface=${attack_surface}, safety_rubric=${safety_rubric}"
  echo "============================================================"

  search_task_query="${attack_surface}_${safety_rubric}"

  # -------- system_prompt_injection --------
  system_prompt_injection=$(python3 - <<EOF
import json
import sys
file_path = "$AGENT_SYSTEM_PROMPT_FILE"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
# Fail fast if key is missing
if query not in tasks:
    raise KeyError(f"Missing injection key: {query}")
value = json.dumps(tasks[query], ensure_ascii=False)
# Remove outer quotes if present
if value.startswith('"') and value.endswith('"'):
    value = value[1:-1]
sys.stdout.write(value)
EOF
)

  echo "[System Prompt Injection]"
  echo "$system_prompt_injection"

  # -------- task_ids --------
  task_ids=$(python3 - <<EOF
import json

file_path = "$DATASET_PATH"
query = "$search_task_query"

with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)

matched_ids = [
    task["id"]
    for task in tasks
    if "id" in task and query in task["id"]
]

print(" ".join(matched_ids))
EOF
)

  echo "[Task IDs]"
  echo "$task_ids"

  # -------- output file --------
  output_file="${OUTPUT_DIR}/${attack_surface}_${safety_rubric}_${MODEL_NAME}.csv"
  touch "$output_file"
  sleep 1

  # -------- vita run --------
  vita run \
    --domain "${DOMAIN}" \
    --user-llm "${USER_LLM}" \
    --dataset-file "${DATASET_FILENAME}" \
    --agent-llm "${MODEL}" \
    --enable-think \
    --evaluator-llm "${EVALUATOR_LLM}" \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps "${MAX_STEPS}" \
    --max-concurrency 1 \
    --csv-output $output_file \
    --language english \
    --system-prompt-injection "$system_prompt_injection"
done

#
attack_surface="user_backdoor"

##
safety_rubrics=(
  "Finance-9"
  "Law-18"
  "Privacy-6"
)
for safety_rubric in "${safety_rubrics[@]}"; do
  echo "============================================================"
  echo "Running attack_surface=${attack_surface}, safety_rubric=${safety_rubric}"
  echo "============================================================"

  search_task_query="${attack_surface}_${safety_rubric}"

  # -------- system_prompt_injection --------
  system_prompt_injection=$(python3 - <<EOF
import json
import sys
file_path = "$AGENT_SYSTEM_PROMPT_FILE"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
if query not in tasks:
    raise KeyError(f"Missing injection key: {query}")
value = json.dumps(tasks[query], ensure_ascii=False)
# Remove outer quotes if present
if value.startswith('"') and value.endswith('"'):
    value = value[1:-1]
sys.stdout.write(value)
EOF
)

  echo "[System Prompt Injection]"
  echo "$system_prompt_injection"

  # -------- task_ids --------
  task_ids=$(python3 - <<EOF
import json

file_path = "$DATASET_PATH"
query = "$search_task_query"

with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)

matched_ids = [
    task["id"]
    for task in tasks
    if "id" in task and query in task["id"]
]

print(" ".join(matched_ids))
EOF
)

  echo "[Task IDs]"
  echo "$task_ids"

  # -------- output file --------
  output_file="${OUTPUT_DIR}/${attack_surface}_${safety_rubric}_${MODEL_NAME}.csv"
  touch "$output_file"
  sleep 1

  vita run \
    --domain "${DOMAIN}" \
    --user-llm "${USER_LLM}" \
    --dataset-file "${DATASET_FILENAME}" \
    --agent-llm "${MODEL}" \
    --enable-think \
    --evaluator-llm "${EVALUATOR_LLM}" \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps "${MAX_STEPS}" \
    --max-concurrency 1 \
    --csv-output $output_file \
    --language english \
    --system-prompt-injection "$system_prompt_injection"
done

#
attack_surface="other_direct"

##
safety_rubrics=(
  "Finance-8"
  "Finance-10"
  "Finance-11"
  "Shopping_Fraud-16"
)
for safety_rubric in "${safety_rubrics[@]}"; do
  echo "============================================================"
  echo "Running attack_surface=${attack_surface}, safety_rubric=${safety_rubric}"
  echo "============================================================"

  search_task_query="${attack_surface}_${safety_rubric}"

  # -------- system_prompt_injection --------
  system_prompt_injection=$(python3 - <<EOF
import json
import sys
file_path = "$AGENT_SYSTEM_PROMPT_FILE"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
if query not in tasks:
    raise KeyError(f"Missing injection key: {query}")
value = json.dumps(tasks[query], ensure_ascii=False)
# Remove outer quotes if present
if value.startswith('"') and value.endswith('"'):
    value = value[1:-1]
sys.stdout.write(value)
EOF
)

  echo "[System Prompt Injection]"
  echo "$system_prompt_injection"

  # -------- task_ids --------
  task_ids=$(python3 - <<EOF
import json

file_path = "$DATASET_PATH"
query = "$search_task_query"

with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)

matched_ids = [
    task["id"]
    for task in tasks
    if "id" in task and query in task["id"]
]

print(" ".join(matched_ids))
EOF
)

  echo "[Task IDs]"
  echo "$task_ids"

  # -------- output file --------
  output_file="${OUTPUT_DIR}/${attack_surface}_${safety_rubric}_${MODEL_NAME}.csv"
  touch "$output_file"
  sleep 1

  vita run \
    --domain "${DOMAIN}" \
    --user-llm "${USER_LLM}" \
    --dataset-file "${DATASET_FILENAME}" \
    --agent-llm "${MODEL}" \
    --enable-think \
    --evaluator-llm "${EVALUATOR_LLM}" \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps "${MAX_STEPS}" \
    --max-concurrency 1 \
    --csv-output $output_file \
    --language english \
    --system-prompt-injection "$system_prompt_injection"
done

#
attack_surface="other_backdoor"

#
safety_rubrics=(
  "Finance-10"
  "Finance-11"
  "Shopping_Fraud-16"
)
for safety_rubric in "${safety_rubrics[@]}"; do
  echo "============================================================"
  echo "Running attack_surface=${attack_surface}, safety_rubric=${safety_rubric}"
  echo "============================================================"

  search_task_query="${attack_surface}_${safety_rubric}"

  # -------- system_prompt_injection --------
  system_prompt_injection=$(python3 - <<EOF
import json
import sys
file_path = "$AGENT_SYSTEM_PROMPT_FILE"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
if query not in tasks:
    raise KeyError(f"Missing injection key: {query}")
value = json.dumps(tasks[query], ensure_ascii=False)
# Remove outer quotes if present
if value.startswith('"') and value.endswith('"'):
    value = value[1:-1]
sys.stdout.write(value)
EOF
)

  echo "[System Prompt Injection]"
  echo "$system_prompt_injection"

  # -------- task_ids --------
  task_ids=$(python3 - <<EOF
import json

file_path = "$DATASET_PATH"
query = "$search_task_query"

with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)

matched_ids = [
    task["id"]
    for task in tasks
    if "id" in task and query in task["id"]
]

print(" ".join(matched_ids))
EOF
)

  echo "[Task IDs]"
  echo "$task_ids"

  # -------- output file --------
  output_file="${OUTPUT_DIR}/${attack_surface}_${safety_rubric}_${MODEL_NAME}.csv"
  touch "$output_file"
  sleep 1

  vita run \
    --domain "${DOMAIN}" \
    --user-llm "${USER_LLM}" \
    --dataset-file "${DATASET_FILENAME}" \
    --agent-llm "${MODEL}" \
    --enable-think \
    --evaluator-llm "${EVALUATOR_LLM}" \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps "${MAX_STEPS}" \
    --max-concurrency 1 \
    --csv-output $output_file \
    --language english \
    --system-prompt-injection "$system_prompt_injection"
done
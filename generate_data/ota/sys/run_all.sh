#!/bin/bash
set -e

# 兼容 Linux：尽量使用 conda 激活环境（若不可用则跳过）
BENCH_CONDA_ENV="${BENCH_CONDA_ENV:-riskybench}"

if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh" || true
  conda activate "$BENCH_CONDA_ENV" || true
fi

##### 配置区域（使用基于项目根的相对路径）#####
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$BENCH_ROOT"

agent_system_prompt_file="generate_prompt/sys/all_injected_agent_system_prompt.json"
agent_system_prompt_attack_tasks_file="data/vita/domains/ota/agent_system_prompt_attack_tasks.json"
output_dir="generate_prompt/sys/output/agent_system_prompt_test"
model="claude-haiku-4-5-20251001"
model_name="claude"
domain="ota"
####

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
file_path = "$agent_system_prompt_file"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
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

file_path = "$agent_system_prompt_attack_tasks_file"
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
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  touch "$output_file"
  sleep 1

  # -------- vita run --------
  vita run \
    --domain $domain \
    --user-llm gpt-4.1 \
    --dataset-file agent_system_prompt_attack_tasks.json \
    --agent-llm $model \
    --enable-think \
    --evaluator-llm gpt-4.1 \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps 100 \
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
file_path = "$agent_system_prompt_file"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
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

file_path = "$agent_system_prompt_attack_tasks_file"
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
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  touch "$output_file"
  sleep 1

  vita run \
    --domain $domain \
    --user-llm gpt-4.1 \
    --dataset-file agent_system_prompt_attack_tasks.json \
    --agent-llm $model \
    --enable-think \
    --evaluator-llm gpt-4.1 \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps 100 \
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
file_path = "$agent_system_prompt_file"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
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

file_path = "$agent_system_prompt_attack_tasks_file"
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
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  touch "$output_file"
  sleep 1

  vita run \
    --domain $domain \
    --user-llm gpt-4.1 \
    --dataset-file agent_system_prompt_attack_tasks.json \
    --agent-llm $model \
    --enable-think \
    --evaluator-llm gpt-4.1 \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps 100 \
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
file_path = "$agent_system_prompt_file"
query = "$search_task_query"
with open(file_path, "r", encoding="utf-8") as f:
    tasks = json.load(f)
# Use json.dumps to properly escape special characters, then remove outer quotes
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

file_path = "$agent_system_prompt_attack_tasks_file"
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
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  touch "$output_file"
  sleep 1

  vita run \
    --domain $domain \
    --user-llm gpt-4.1 \
    --dataset-file agent_system_prompt_attack_tasks.json \
    --agent-llm $model \
    --enable-think \
    --evaluator-llm gpt-4.1 \
    --task-ids $task_ids \
    --num-trials 1 \
    --max-steps 100 \
    --max-concurrency 1 \
    --csv-output $output_file \
    --language english \
    --system-prompt-injection "$system_prompt_injection"
done
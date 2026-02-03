#!/bin/bash

set -euo pipefail

# =============== 匿名化说明 ===============
# - 本脚本仅使用相对路径（基于仓库根目录）
# - 工具脚本 `vita_utils.py` 与本文件同级：`src/vita_utils.py`
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

##### 配置区域（均可通过环境变量覆盖） #####
OUTPUT_DIR="${OUTPUT_DIR:-./output/sys_attack_eval}"
MODEL_NAME="${MODEL_NAME:-claude}"
MERGED_SIMULATION_FILE="${MERGED_SIMULATION_FILE:-${OUTPUT_DIR}/process_simulations/${MODEL_NAME}_simulations.json}"
mkdir -p "$(dirname "${MERGED_SIMULATION_FILE}")"

all_output_files=()

##### RUN #####
#
if compgen -G "${OUTPUT_DIR}/*.csv" > /dev/null; then
  for csv in "${OUTPUT_DIR}"/*.csv; do
    all_output_files+=("${csv}")
  done
else
  echo "[ERROR] No CSV files found under: ${OUTPUT_DIR}"
  echo "Run 'bash src/run_all.sh' first, or set OUTPUT_DIR to the directory containing CSV outputs."
  exit 1
fi

all_simulation_jsons=()

for csv_file in "${all_output_files[@]}"; do
  # 提取第 3 列
  json_path=$(awk -F',' 'NF>=3{print $3}' "$csv_file" | head -n 1)

  # 防止空值
  if [[ -n "$json_path" ]]; then
    all_simulation_jsons+=("$json_path")
  fi
done

# 变成空格分隔的字符串
echo "All simulation json paths:"
printf '%s\n' "${all_simulation_jsons[@]}"

python3 "${SCRIPT_DIR}/vita_utils.py" merge "${all_simulation_jsons[@]}" -o "${MERGED_SIMULATION_FILE}"

echo "[OK] Merged simulation saved to: ${MERGED_SIMULATION_FILE}"
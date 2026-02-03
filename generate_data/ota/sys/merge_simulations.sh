#!/bin/bash

##### 配置区域（使用相对于项目根的路径）#####
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
output_dir="${BENCH_ROOT}/output/agent_system_prompt_test"
model_name="deepseek"
merged_simulation_file="${output_dir}/process_simulations/${model_name}_simulations.json"
# vita_utils.py 位于项目根目录
####

all_output_files=()

##### RUN #####
#
attack_surface="user_direct"
##
safety_rubrics=(
  "Finance-9"
  "Law-18"
  "Privacy-6"
)
for safety_rubric in "${safety_rubrics[@]}"; do
  # -------- output file --------
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  all_output_files+=("$output_file")
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
  # -------- output file --------
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  all_output_files+=("$output_file")
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
  # -------- output file --------
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  all_output_files+=("$output_file")
done

#
attack_surface="other_backdoor"
##
safety_rubrics=(
  "Finance-10"
  "Finance-11"
  "Shopping_Fraud-16"
)
for safety_rubric in "${safety_rubrics[@]}"; do
  # -------- output file --------
  output_file="${output_dir}/${attack_surface}_${safety_rubric}_${model_name}.csv"
  all_output_files+=("$output_file")
done

all_simulation_jsons=()

for csv_file in "${all_output_files[@]}"; do
  # 提取第 3 列
  json_path=$(awk -F',' '{print $3}' "$csv_file")

  # 防止空值
  if [[ -n "$json_path" ]]; then
    all_simulation_jsons+=("$json_path")
  fi
done

# 变成空格分隔的字符串
all_simulation_jsons_str="${all_simulation_jsons[*]}"

echo "All simulation json paths:"
echo "$all_simulation_jsons_str"

python "${BENCH_ROOT}/vita_utils.py" merge $all_simulation_jsons_str -o $merged_simulation_file
#!/bin/bash
# 使用基于项目根的相对路径，兼容 Linux
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

##### 配置区域（相对于 bench 项目根）#####
output_dir="${BENCH_ROOT}/generate_data/delivery/Del-sys/agent_system_prompt_final/result"
model_name="deepseek"
merged_simulation_file="${BENCH_ROOT}/generate_data/delivery/Del-sys/agent_system_prompt_final/merge_result/${model_name}_sys.json"

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

python3 "${SCRIPT_DIR}/vita_utils.py" merge $all_simulation_jsons_str -o "$merged_simulation_file"
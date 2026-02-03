#!/usr/bin/env bash
# Unified entry point for instore domain data generation
# Usage: bash run_generate.sh <original_file> <start_idx> <number_of_tasks> <output_path>
# Example: bash run_generate.sh ./data/vita/domains/instore/tasks_en.json 0 2 ./data/vita/domains/instore/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INITIAL_PWD="${PWD}"
cd "$SCRIPT_DIR"

# Required arguments (relative paths are interpreted relative to the current directory where the script is invoked)
original_file="${1:-}"
start_idx="${2:-0}"
number_of_tasks="${3:-}"
output_path="${4:-./data/vita/domains/instore}"

# Convert to absolute paths so Python can still find files when executed under the instore directory
[ -n "$original_file" ] && [[ "$original_file" != /* ]] && original_file="${INITIAL_PWD}/${original_file}"
[ -n "$output_path" ] && [[ "$output_path" != /* ]] && output_path="${INITIAL_PWD}/${output_path}"

# Argument count check (at minimum, original_file and number_of_tasks are required)
if [ -z "$original_file" ] || [ -z "$number_of_tasks" ]; then
    echo "Usage: bash run_generate.sh <original_file> <start_idx> <number_of_tasks> <output_path>"
    echo "  original_file   - Path to the original English data file (relative or absolute)"
    echo "  start_idx       - Starting index in the original data (default: 0)"
    echo "  number_of_tasks - Total number of tasks to generate"
    echo "  output_path     - Output directory (default: ./data/vita/domains/instore/)"
    exit 1
fi

# Default start_idx
if [ -z "$start_idx" ] || [ "$start_idx" = "" ]; then
    start_idx=0
fi

# Environment variable checks
if [ -z "${API_KEY:-}" ]; then
    echo "Error: Please set the environment variable API_KEY"
    exit 1
fi
if [ -z "${BASE_URL:-}" ]; then
    echo "Warning: BASE_URL is not set. Using the default value https://www.openai.com/v1"
    export BASE_URL="https://www.openai.com/v1"
fi

# Normalize BASE_URL: avoid providing a full endpoint (/chat/completions) that the SDK would append again
BASE_URL="${BASE_URL//$'\r'/}"
BASE_URL="${BASE_URL%%/chat/completions*}"
BASE_URL="${BASE_URL%/}"
export BASE_URL
if [ -z "${MODEL_NAME:-}" ]; then
    echo "Error: Please set the environment variable MODEL_NAME"
    exit 1
fi

# Auto-create output directory
mkdir -p "$output_path"

# Normalize output_path (remove trailing / for consistent path concatenation)
output_path="${output_path%/}"

# Generate data for each attack surface (ui / tf / sys have been integrated into the unified argument interface)
# Naming format: instore_{ui|tf|sys}_{num_tasks}_en.json
# Note: ms (message_history) and env (env_noise) scripts have not been integrated into the 4-argument interface yet.
#       Run them separately or merge later.

run_python() {
    local script="$1"
    local out_file="$2"
    if [ ! -f "$script" ]; then
        echo "Warning: Script does not exist, skipping: $script"
        return 0
    fi
    echo ">>> Running: $script -> $out_file"
    if ! python3 "$script" "$original_file" "$start_idx" "$number_of_tasks" "$out_file"; then
        echo "Error: Execution failed: $script"
        exit 1
    fi
}

# user_instruction -> ui
run_python "ui/generate_tasks_instore_ui.py" "${output_path}/instore_ui_${number_of_tasks}_en.json"

# tool_feedback -> tf
run_python "tf/generate_tasks_instore_tf.py" "${output_path}/instore_tf_${number_of_tasks}_en.json"

# system_prompt -> sys (depends on original files under sys/user_direct/)
run_python "sys/generate_tasks_instore_sys.py" "${output_path}/instore_sys_${number_of_tasks}_en.json"

echo "Instore data generation completed. Output directory: $output_path"

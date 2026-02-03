#!/usr/bin/env bash
# Unified entry point for data generation in the delivery domain
# Usage: bash run_generate.sh <original_file> <start_idx> <number_of_tasks> <output_path>
# Example: bash run_generate.sh ./data/vita/domains/delivery/tasks_en.json 0 2 ./data/vita/domains/delivery/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INITIAL_PWD="${PWD}"
cd "$SCRIPT_DIR"

# Mandatory parameters (relative paths are resolved relative to the current working directory)
original_file="${1:-}"
start_idx="${2:-0}"
number_of_tasks="${3:-}"
output_path="${4:-./data/vita/domains/delivery}"

# Convert to absolute paths to ensure files are found when executing Python in the delivery directory
[ -n "$original_file" ] && [[ "$original_file" != /* ]] && original_file="${INITIAL_PWD}/${original_file}"
[ -n "$output_path" ] && [[ "$output_path" != /* ]] && output_path="${INITIAL_PWD}/${output_path}"

# Argument count check (requires at least original_file and number_of_tasks)
if [ -z "$original_file" ] || [ -z "$number_of_tasks" ]; then
    echo "Usage: bash run_generate.sh <original_file> <start_idx> <number_of_tasks> <output_path>"
    echo "  original_file    - Path to the original English data file (relative or absolute)"
    echo "  start_idx        - Start index of original data (default 0)"
    echo "  number_of_tasks  - Total number of tasks to generate"
    echo "  output_path      - Data output directory (default ./data/vita/domains/delivery/)"
    exit 1
fi

# Default start_idx
if [ -z "$start_idx" ] || [ "$start_idx" = "" ]; then
    start_idx=0
fi

# Environment variable check
if [ -z "${API_KEY:-}" ]; then
    echo "Error: Please set the API_KEY environment variable"
    exit 1
fi
if [ -z "${BASE_URL:-}" ]; then
    echo "Warning: BASE_URL environment variable not set, using default https://www.openai.com/v1"
    export BASE_URL="https://www.openai.com/v1"
fi

# Normalize BASE_URL: Prevent double-splicing by SDK if the full endpoint (/chat/completions) is mistakenly provided
BASE_URL="${BASE_URL//$'\r'/}"
BASE_URL="${BASE_URL%%/chat/completions*}"
BASE_URL="${BASE_URL%/}"
export BASE_URL
if [ -z "${MODEL_NAME:-}" ]; then
    echo "Error: Please set the MODEL_NAME environment variable"
    exit 1
fi

# Automatically create output directory
mkdir -p "$output_path"

# Normalize output_path (remove trailing / for consistent concatenation)
output_path="${output_path%/}"

# Call the unified Python entry point
if ! python3 run_generate.py "$original_file" "$start_idx" "$number_of_tasks" "$output_path"; then
    echo "Error: Python data generation execution failed"
    exit 1
fi

echo "Delivery data generation complete. Output directory: $output_path"

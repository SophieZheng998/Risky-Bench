#!/bin/bash

# ==================== Unified OTA Domain Data Generation Script ====================
# Usage: bash run_generate.sh <original_file> <start_idx> <number_of_tasks> <output_path> [attack_surface]
# Parameters:
#   original_file: Path to the original English data file
#   start_idx: Starting index in the original data (default: 0)
#   number_of_tasks: Total number of tasks to generate
#   output_path: Output directory (default: ./data/vita/domains/ota/)
#   attack_surface: Attack surface type (optional; ui/env/tf/ms/sys; default: generate all)

set -e  # Exit immediately on error

# Get the script directory and the working directory at invocation time (for resolving relative paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INITIAL_PWD="${PWD}"
cd "$SCRIPT_DIR"

# ==================== Argument Parsing ====================
if [ $# -lt 3 ]; then
    echo "Usage: bash run_generate.sh <original_file> <start_idx> <number_of_tasks> <output_path> [attack_surface]"
    echo ""
    echo "Parameters:"
    echo "  original_file    Path to the original English data file (relative or absolute)"
    echo "  start_idx        Starting index in the original data (default: 0)"
    echo "  number_of_tasks  Total number of tasks to generate"
    echo "  output_path      Output directory (default: ./data/vita/domains/ota/)"
    echo "  attack_surface   Attack surface type (optional; ui/env/tf/ms/sys; default: generate all)"
    echo ""
    echo "Attack surface mapping:"
    echo "  ui  - user_instruction"
    echo "  env - env_noise"
    echo "  tf  - tool_feedback"
    echo "  ms  - message_history"
    echo "  sys - system_prompt"
    exit 1
fi

ORIGINAL_FILE="$1"
START_IDX="${2:-0}"
NUMBER_OF_TASKS="$3"
OUTPUT_PATH="${4:-./data/vita/domains/ota/}"
ATTACK_SURFACE="${5:-all}"

# Convert to absolute paths (relative paths are resolved against the invocation directory; convenient when running from repo root)
if [[ -n "$ORIGINAL_FILE" && ! "$ORIGINAL_FILE" =~ ^/ ]]; then
    ORIGINAL_FILE="${INITIAL_PWD}/${ORIGINAL_FILE#./}"
fi
if [[ -n "$OUTPUT_PATH" && ! "$OUTPUT_PATH" =~ ^/ ]]; then
    OUTPUT_PATH="${INITIAL_PWD}/${OUTPUT_PATH#./}"
fi
OUTPUT_PATH="${OUTPUT_PATH%/}"

# ==================== Environment Variable Checks ====================
if [ -z "$API_KEY" ]; then
    echo "Error: Environment variable API_KEY is not set"
    echo "Please set it first: export API_KEY='YOUR_MODEL_API_KEY'"
    exit 1
fi

if [ -z "$BASE_URL" ]; then
    echo "Warning: BASE_URL is not set. Using the default value https://www.openai.com/v1"
    export BASE_URL="${BASE_URL:-https://www.openai.com/v1}"
fi

# Normalize BASE_URL: avoid providing a full endpoint (/chat/completions) that the SDK would append again
BASE_URL="${BASE_URL//$'\r'/}"
BASE_URL="${BASE_URL%%/chat/completions*}"
BASE_URL="${BASE_URL%/}"
export BASE_URL

if [ -z "$MODEL_NAME" ]; then
    echo "Warning: MODEL_NAME is not set. Using the default value"
    export MODEL_NAME="${MODEL_NAME:-gpt-4.1}"
fi

# ==================== File Checks ====================
if [ ! -f "$ORIGINAL_FILE" ]; then
    echo "Error: Original file ${ORIGINAL_FILE} does not exist"
    exit 1
fi

# ==================== Create Output Directory ====================
mkdir -p "$OUTPUT_PATH"
if [ ! -w "$OUTPUT_PATH" ]; then
    echo "Error: No write permission for ${OUTPUT_PATH}"
    exit 1
fi

# ==================== Attack Surface Mapping ====================
declare -A ATTACK_SURFACE_MAP
ATTACK_SURFACE_MAP["ui"]="user_instruction"
ATTACK_SURFACE_MAP["env"]="env_noise"
ATTACK_SURFACE_MAP["tf"]="tool_feedback"
ATTACK_SURFACE_MAP["ms"]="message_history"
ATTACK_SURFACE_MAP["sys"]="system_prompt"

# ==================== Generation Functions ====================
generate_ui() {
    echo "=========================================="
    echo "Generating user_instruction (ui) data..."
    echo "=========================================="
    python3 "$SCRIPT_DIR/generate_user_ins_en_tasks.py" \
        "$ORIGINAL_FILE" \
        "$START_IDX" \
        "$NUMBER_OF_TASKS" \
        "$OUTPUT_PATH/ota_ui_${NUMBER_OF_TASKS}_en.json"

    if [ $? -ne 0 ]; then
        echo "Error: user_instruction generation failed"
        return 1
    fi
    echo "✓ user_instruction generation succeeded"
}

generate_env() {
    echo "=========================================="
    echo "Generating env_noise (env) data..."
    echo "=========================================="
    python3 "$SCRIPT_DIR/generate_tasks_env_indirect_ota.py" \
        "$ORIGINAL_FILE" \
        "$START_IDX" \
        "$NUMBER_OF_TASKS" \
        "$OUTPUT_PATH/ota_env_${NUMBER_OF_TASKS}_en.json"

    if [ $? -ne 0 ]; then
        echo "Error: env_noise generation failed"
        return 1
    fi
    echo "✓ env_noise generation succeeded"
}

generate_tf() {
    echo "=========================================="
    echo "Generating tool_feedback (tf) data..."
    echo "=========================================="
    python3 "$SCRIPT_DIR/generate_tasks_tf_ota.py" \
        "$ORIGINAL_FILE" \
        "$START_IDX" \
        "$NUMBER_OF_TASKS" \
        "$OUTPUT_PATH/ota_tf_${NUMBER_OF_TASKS}_en.json"

    if [ $? -ne 0 ]; then
        echo "Error: tool_feedback generation failed"
        return 1
    fi
    echo "✓ tool_feedback generation succeeded"
}

generate_ms() {
    echo "=========================================="
    echo "Generating message_history (ms) data..."
    echo "=========================================="
    python3 "$SCRIPT_DIR/generate_tasks_ms_ota.py" \
        "$ORIGINAL_FILE" \
        "$START_IDX" \
        "$NUMBER_OF_TASKS" \
        "$OUTPUT_PATH/ota_ms_${NUMBER_OF_TASKS}_en.json"

    if [ $? -ne 0 ]; then
        echo "Error: message_history generation failed"
        return 1
    fi
    echo "✓ message_history generation succeeded"
}

generate_sys() {
    echo "=========================================="
    echo "Generating system_prompt (sys) data..."
    echo "=========================================="
    python3 "$SCRIPT_DIR/generate_tasks_sys_ota.py" \
        "$ORIGINAL_FILE" \
        "$START_IDX" \
        "$NUMBER_OF_TASKS" \
        "$OUTPUT_PATH/ota_sys_${NUMBER_OF_TASKS}_en.json"

    if [ $? -ne 0 ]; then
        echo "Error: system_prompt generation failed"
        return 1
    fi
    echo "✓ system_prompt generation succeeded"
}

# ==================== Main Execution ====================
echo "=========================================="
echo "OTA domain data generation started"
echo "=========================================="
echo "Original file: $ORIGINAL_FILE"
echo "Start index:   $START_IDX"
echo "Task count:    $NUMBER_OF_TASKS"
echo "Output path:   $OUTPUT_PATH"
echo "Attack surface:$ATTACK_SURFACE"
echo "=========================================="

ERROR_COUNT=0

if [ "$ATTACK_SURFACE" = "all" ]; then
    # Generate all attack surfaces
    generate_ui || ((ERROR_COUNT++))
    generate_env || ((ERROR_COUNT++))
    generate_tf || ((ERROR_COUNT++))
    generate_ms || ((ERROR_COUNT++))
    generate_sys || ((ERROR_COUNT++))
else
    # Generate the specified attack surface
    case "$ATTACK_SURFACE" in
        ui)
            generate_ui || ((ERROR_COUNT++))
            ;;
        env)
            generate_env || ((ERROR_COUNT++))
            ;;
        tf)
            generate_tf || ((ERROR_COUNT++))
            ;;
        ms)
            generate_ms || ((ERROR_COUNT++))
            ;;
        sys)
            generate_sys || ((ERROR_COUNT++))
            ;;
        *)
            echo "Error: Invalid attack surface type '$ATTACK_SURFACE'"
            echo "Supported values: ui, env, tf, ms, sys, all"
            exit 1
            ;;
    esac
fi

# ==================== Summary ====================
echo ""
echo "=========================================="
if [ $ERROR_COUNT -eq 0 ]; then
    echo "✓ All data generation completed!"
    echo "Output files are located at: $OUTPUT_PATH"
    ls -lh "$OUTPUT_PATH"/*.json 2>/dev/null || echo "(No output files found)"
else
    echo "✗ Data generation completed, but $ERROR_COUNT attack surface(s) failed"
    exit 1
fi
echo "=========================================="

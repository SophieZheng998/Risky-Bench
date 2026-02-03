#!/bin/bash

# Configuration Variables
API_KEY="YOUR_API_KEY_HERE"
API_BASE="YOUR_API_BASE_HERE"
MODEL_NAME="YOUR_EVALUATOR_MODEL_NAME_HERE"
BASE_DIR="YOUR_BASE_DIRECTORY_HERE"
TARGET_DIR="$BASE_DIR/target_model" # Replaced specific model folder name

# ------------------------------------------------------------------------------
# UI Scenario 
# ------------------------------------------------------------------------------
python "$BASE_DIR/automated_evaluator.py" \
    "$TARGET_DIR/model_ui.json" \
    --type ui \
    --output "$TARGET_DIR/model_ui_eva.csv" \
    --api-base "$API_BASE" \
    --api-key "$API_KEY" \
    --model "$MODEL_NAME" \
    --thinking

# ------------------------------------------------------------------------------
# Environment Scenario 
# ------------------------------------------------------------------------------
python "$BASE_DIR/automated_evaluator.py" \
    "$TARGET_DIR/model_env.json" \
    --type env \
    --output "$TARGET_DIR/model_env_eva.csv" \
    --api-base "$API_BASE" \
    --api-key "$API_KEY" \
    --model "$MODEL_NAME" \
    --thinking

# ------------------------------------------------------------------------------
# Memory Scenario 
# ------------------------------------------------------------------------------
python "$BASE_DIR/automated_evaluator.py" \
    "$TARGET_DIR/model_ms.json" \
    --type ms \
    --output "$TARGET_DIR/model_ms_eva.csv" \
    --api-base "$API_BASE" \
    --api-key "$API_KEY" \
    --model "$MODEL_NAME" \
    --thinking

# ------------------------------------------------------------------------------
# Tool Scenario 
# ------------------------------------------------------------------------------
python "$BASE_DIR/automated_evaluator.py" \
    "$TARGET_DIR/model_tf.json" \
    --type tool \
    --output "$TARGET_DIR/model_tf_eva.csv" \
    --api-base "$API_BASE" \
    --api-key "$API_KEY" \
    --model "$MODEL_NAME" \
    --thinking

# ------------------------------------------------------------------------------
# System Prompt Scenario 
# ------------------------------------------------------------------------------
python "$BASE_DIR/automated_evaluator.py" \
    "$TARGET_DIR/model_sys.json" \
    --type sys \
    --output "$TARGET_DIR/model_sys_eva.csv" \
    --api-base "$API_BASE" \
    --api-key "$API_KEY" \
    --model "$MODEL_NAME" \
    --injection-file "YOUR_all_injected_agent_system_prompt.json_DATA_PATH" \
    --thinking
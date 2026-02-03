#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
delivery 领域数据生成统一入口。
从 run_generate.sh 接收 4 个参数，按公告规范输出 delivery_{攻击面}_{任务数}_en.json。
攻击面：ui (user_instruction)、env (env_noise)、ms (message_history)。
tf、sys 暂未接入统一入口，可后续扩展。
"""
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOMAIN = "delivery"

# 攻击面缩写 -> (脚本相对路径, 描述)
SURFACE_SCRIPTS = {
    "ui": ("Delivery-User/generate_tasks_en.py", "user_instruction"),
    "env": ("Delivery-Environmental/generate_task_en.py", "env_noise"),
    "ms": ("Del-mem/generate_message_history_tasks_backdoor.py", "message_history"),
}


def main():
    if len(sys.argv) < 5:
        print("用法: python3 run_generate.py <original_file> <start_idx> <number_of_tasks> <output_path>", file=sys.stderr)
        sys.exit(1)

    original_file = sys.argv[1]
    start_idx = sys.argv[2]
    number_of_tasks = sys.argv[3]
    output_path = sys.argv[4]

    # 统一使用正斜杠，兼容 Linux
    original_file = os.path.normpath(original_file).replace("\\", "/")
    output_path = os.path.normpath(output_path).replace("\\", "/").rstrip("/")

    # 1. 原始文件不存在
    if not os.path.isfile(original_file):
        print(f"Error: 原始文件 {original_file} 不存在", file=sys.stderr)
        sys.exit(1)

    # 2. 输出目录：自动创建并检查可写
    try:
        os.makedirs(output_path, exist_ok=True)
    except OSError as e:
        print(f"Error: 无法创建输出路径 {output_path}: {e}", file=sys.stderr)
        sys.exit(1)
    test_file = os.path.join(output_path, ".write_test")
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            pass
        os.remove(test_file)
    except (OSError, PermissionError):
        print(f"Error: 无权限写入路径 {output_path}", file=sys.stderr)
        sys.exit(1)

    # 3. 环境变量（shell 已检查，此处再确认）
    if not os.environ.get("API_KEY") or not os.environ.get("BASE_URL") or not os.environ.get("MODEL_NAME"):
        print("Error: 请设置环境变量 API_KEY, BASE_URL, MODEL_NAME", file=sys.stderr)
        sys.exit(1)

    # 4. 依次调用各攻击面生成脚本
    for surface, (script_rel, _) in SURFACE_SCRIPTS.items():
        script_path = os.path.join(SCRIPT_DIR, script_rel.replace("/", os.sep))
        if not os.path.isfile(script_path):
            print(f"Warning: 脚本不存在，跳过 {surface}: {script_path}")
            continue
        out_file = os.path.join(output_path, f"{DOMAIN}_{surface}_{number_of_tasks}_en.json").replace("\\", "/")
        cmd = [
            sys.executable,
            script_path,
            original_file,
            str(start_idx),
            str(number_of_tasks),
            out_file,
        ]
        print(f">>> 运行: {surface} -> {out_file}")
        try:
            ret = subprocess.run(cmd, cwd=SCRIPT_DIR, check=False)
            if ret.returncode != 0:
                print(f"Error: 执行失败 {surface}，退出码 {ret.returncode}", file=sys.stderr)
                sys.exit(ret.returncode)
        except Exception as e:
            print(f"Error: 调用脚本异常 {surface}: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Success: delivery 数据生成完成，输出目录: {output_path}")


if __name__ == "__main__":
    main()

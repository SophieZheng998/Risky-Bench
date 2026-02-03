#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OTA领域 system_prompt 攻击面数据生成脚本
根据公告要求，统一调用接口
"""

import json
import os
import sys
import argparse
import copy

def process_system_prompt(input_file, start_idx, number_of_tasks, output_file):
    """
    处理system_prompt攻击面数据生成
    
    注意：system_prompt攻击面的生成逻辑较为复杂，涉及多个步骤。
    本脚本提供一个简化的统一接口，实际使用时可能需要根据具体需求调整。
    """
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"Error: 原始文件 {input_file} 不存在")
        return False
    
    # 读取输入文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            all_tasks = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        return False
    
    # 根据start_idx和number_of_tasks切片数据
    if number_of_tasks is not None:
        end_idx = min(start_idx + number_of_tasks, len(all_tasks))
        tasks = all_tasks[start_idx:end_idx]
        print(f"Processing tasks {start_idx} to {end_idx-1} (total {len(tasks)} tasks)...")
    else:
        tasks = all_tasks[start_idx:]
        print(f"Processing tasks from {start_idx} to end (total {len(tasks)} tasks)...")
    
    # 处理每个任务
    # 注意：system_prompt攻击面通常不需要修改任务本身，而是通过外部注入system prompt
    # 这里我们只是简单地复制任务，实际使用时可能需要根据具体需求调整
    processed_tasks = []
    for task in tasks:
        new_task = copy.deepcopy(task)
        
        # 如果需要，可以在这里添加system_prompt相关的标记
        # 例如：添加一个标记字段表示这个任务需要system_prompt攻击
        if "safety_annotation" not in new_task:
            new_task["safety_annotation"] = {}
        new_task["safety_annotation"]["attack_surface"] = "system_prompt"
        
        processed_tasks.append(new_task)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"Error: 无法创建输出目录 {output_dir}: {e}")
            return False
    
    # 保存结果
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_tasks, f, ensure_ascii=False, indent=4)
        print(f"Done. Saved {len(processed_tasks)} tasks to {output_file}")
        print("Note: system_prompt攻击面通常需要外部注入system prompt，请参考sys/目录下的相关脚本")
        return True
    except PermissionError:
        print(f"Error: 无权限写入路径 {output_file}")
        return False
    except Exception as e:
        print(f"Error saving output: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='生成OTA领域的system_prompt攻击面数据')
    parser.add_argument('original_file', type=str, help='原始英文数据文件路径')
    parser.add_argument('start_idx', type=int, nargs='?', default=0, help='原始数据起始序号（默认0）')
    parser.add_argument('number_of_tasks', type=int, nargs='?', default=None, help='生成任务总数（默认处理所有任务）')
    parser.add_argument('output_file', type=str, help='输出文件路径')
    
    args = parser.parse_args()
    
    success = process_system_prompt(
        args.original_file,
        args.start_idx,
        args.number_of_tasks,
        args.output_file
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

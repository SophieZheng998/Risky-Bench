#!/usr/bin/env python3
"""
辅助工具脚本（匿名版）
支持两种功能：
1. 合并多个 simulation 结果文件
2. 处理 OTA tasks JSON 文件（清空 expected_states，只保留最后一个 overall_rubrics）

用法:
    # 合并 simulation 结果
    python vita_utils.py merge file1.json file2.json ... -o merged.json
    
    # 处理 OTA tasks
    python vita_utils.py process-tasks input.json output.json --backup
"""

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List


# ==================== 合并 Simulation 结果 ====================

def merge_results(files: List[Path], output: Path, deduplicate: bool = True):
    """
    合并多个 Results 文件
    
    Args:
        files: 要合并的文件路径列表
        output: 输出文件路径
        deduplicate: 是否去重（基于 task_id, trial, seed）
    """
    if not files:
        raise ValueError("至少需要提供一个输入文件")
    
    # 加载所有结果
    all_results = []
    for file_path in files:
        if not file_path.exists():
            print(f"警告: 文件不存在，跳过: {file_path}")
            continue
        print(f"加载文件: {file_path}")
        from vita.data_model.simulation import Results
        results = Results.load(file_path)
        all_results.append(results)
        print(f"  - 包含 {len(results.simulations)} 个 simulations")
    
    if not all_results:
        raise ValueError("没有有效的输入文件")
    
    # 使用第一个文件的 info 和 tasks 作为基础
    base_results = all_results[0]
    merged_simulations = base_results.simulations.copy()
    merged_tasks = {task.id: task for task in base_results.tasks}
    
    # 合并其他文件
    for results in all_results[1:]:
        # 合并 tasks（去重）
        for task in results.tasks:
            if task.id not in merged_tasks:
                merged_tasks[task.id] = task
        
        # 合并 simulations
        merged_simulations.extend(results.simulations)
    
    # 去重（如果需要）
    if deduplicate:
        seen = set()
        unique_simulations = []
        for sim in merged_simulations:
            # 使用 (task_id, trial, seed) 作为唯一标识
            key = (sim.task_id, sim.trial, sim.seed)
            if key not in seen:
                seen.add(key)
                unique_simulations.append(sim)
            else:
                print(f"去重: 跳过重复的 simulation {sim.task_id} (trial={sim.trial}, seed={sim.seed})")
        merged_simulations = unique_simulations
    
    # 创建合并后的 Results 对象
    from vita.data_model.simulation import Results
    merged_results = Results(
        timestamp=base_results.timestamp,
        info=base_results.info,
        tasks=list(merged_tasks.values()),
        simulations=merged_simulations,
    )
    
    # 保存结果
    output.parent.mkdir(parents=True, exist_ok=True)
    merged_results.save(output)
    
    print(f"\n合并完成!")
    print(f"  - 输入文件数: {len(files)}")
    print(f"  - 总 simulations: {len(merged_simulations)}")
    print(f"  - 总 tasks: {len(merged_tasks)}")
    print(f"  - 输出文件: {output}")


# ==================== 处理 OTA Tasks ====================

def process_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理单个 task：
    1. 清空 expected_states 数组
    2. 只保留 overall_rubrics 的最后一个元素
    """
    # 处理 expected_states
    if "evaluation_criteria" in task:
        if "expected_states" in task["evaluation_criteria"]:
            # 清空 expected_states 数组
            task["evaluation_criteria"]["expected_states"] = []
        
        # 处理 overall_rubrics
        if "overall_rubrics" in task["evaluation_criteria"]:
            rubrics = task["evaluation_criteria"]["overall_rubrics"]
            if isinstance(rubrics, list) and len(rubrics) > 0:
                # 只保留最后一个 rubrics
                task["evaluation_criteria"]["overall_rubrics"] = [rubrics[-1]]
            elif isinstance(rubrics, list):
                # 如果为空，保持为空
                task["evaluation_criteria"]["overall_rubrics"] = []
    
    return task


def process_json_file(input_path: Path, output_path: Path, create_backup: bool = False):
    """
    处理 JSON 文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        create_backup: 是否创建备份
    """
    # 创建备份
    if create_backup:
        backup_path = input_path.with_suffix(input_path.suffix + ".backup")
        print(f"创建备份文件: {backup_path}")
        shutil.copy2(input_path, backup_path)
    
    # 读取 JSON 文件
    print(f"读取文件: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    if not isinstance(tasks, list):
        raise ValueError("JSON 文件应该包含一个 task 数组")
    
    print(f"找到 {len(tasks)} 个 tasks")
    
    # 统计信息
    stats = {
        "total_tasks": len(tasks),
        "tasks_with_expected_states": 0,
        "tasks_with_rubrics": 0,
        "total_rubrics_removed": 0,
    }
    
    # 处理每个 task
    for i, task in enumerate(tasks):
        if "evaluation_criteria" in task:
            # 统计 expected_states
            if "expected_states" in task["evaluation_criteria"]:
                if len(task["evaluation_criteria"]["expected_states"]) > 0:
                    stats["tasks_with_expected_states"] += 1
            
            # 统计和处理 rubrics
            if "overall_rubrics" in task["evaluation_criteria"]:
                rubrics = task["evaluation_criteria"]["overall_rubrics"]
                if isinstance(rubrics, list) and len(rubrics) > 0:
                    stats["tasks_with_rubrics"] += 1
                    original_count = len(rubrics)
                    # 处理 task
                    task = process_task(task)
                    # 计算删除的数量
                    if len(task["evaluation_criteria"]["overall_rubrics"]) < original_count:
                        stats["total_rubrics_removed"] += (original_count - 1)
        
        # 处理 task（即使没有 evaluation_criteria 也要处理，确保 expected_states 被清空）
        task = process_task(task)
        tasks[i] = task
    
    # 保存处理后的文件
    print(f"保存到: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    
    # 打印统计信息
    print("\n处理完成！")
    print(f"  - 总 tasks: {stats['total_tasks']}")
    print(f"  - 包含 expected_states 的 tasks: {stats['tasks_with_expected_states']}")
    print(f"  - 包含 overall_rubrics 的 tasks: {stats['tasks_with_rubrics']}")
    print(f"  - 删除的 rubrics 总数: {stats['total_rubrics_removed']}")


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(
        description="辅助工具脚本（匿名版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 合并命令
    merge_parser = subparsers.add_parser(
        "merge",
        help="合并多个 simulation 结果文件",
        description="合并多个 simulation 结果文件",
    )
    merge_parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="要合并的 simulation 文件路径",
    )
    merge_parser.add_argument(
        "-o", "--output",
        type=Path,
        required=True,
        help="输出文件路径",
    )
    merge_parser.add_argument(
        "--no-deduplicate",
        action="store_true",
        help="不去重（保留所有 simulations，包括重复的）",
    )
    
    # 处理 tasks 命令
    process_parser = subparsers.add_parser(
        "process-tasks",
        help="处理 OTA tasks JSON 文件",
        description="处理 OTA tasks JSON 文件：清空 expected_states，只保留最后一个 overall_rubrics",
    )
    process_parser.add_argument(
        "input",
        type=Path,
        help="输入 JSON 文件路径",
    )
    process_parser.add_argument(
        "output",
        type=Path,
        help="输出 JSON 文件路径",
    )
    process_parser.add_argument(
        "--backup",
        action="store_true",
        help="创建输入文件的备份",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "merge":
        merge_results(
            files=args.files,
            output=args.output,
            deduplicate=not args.no_deduplicate,
        )
    elif args.command == "process-tasks":
        if not args.input.exists():
            raise FileNotFoundError(f"输入文件不存在: {args.input}")
        process_json_file(
            input_path=args.input,
            output_path=args.output,
            create_backup=args.backup,
        )


if __name__ == "__main__":
    main()

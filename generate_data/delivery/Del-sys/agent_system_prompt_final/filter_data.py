import json
import os

# 项目根路径（基于脚本位置，兼容 Linux）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, '..', '..', '..', '..'))

def filter_json_by_ids(input_file, output_file, target_ids):
    """
    读取 JSON 文件，保留 id 在 target_ids 中的对象，并保存到新文件。
    
    :param input_file: 输入的 JSON 文件路径
    :param output_file: 输出的 JSON 文件路径
    :param target_ids: 需要保留的 id 列表 (可以是数字或字符串，需与源文件类型一致)
    """
    try:
        # 1. 读取原始 JSON 文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 确保数据是一个列表
        if not isinstance(data, list):
            print("错误：JSON 文件内容必须是一个对象列表。")
            return

        print(f"原始数据包含 {len(data)} 个对象。")

        # 2. 筛选数据
        # 使用 set 提高查找速度，尤其是当 target_ids 数量很大时
        target_ids_set = set(target_ids)
        
        filtered_data = [obj for obj in data if obj.get('id') in target_ids_set]

        # 3. 保存到新文件
        with open(output_file, 'w', encoding='utf-8') as f:
            # ensure_ascii=False 保证中文字符正常显示
            # indent=4 美化输出格式
            json.dump(filtered_data, f, ensure_ascii=False, indent=4)

        print(f"筛选完成。保留了 {len(filtered_data)} 个对象。")
        print(f"结果已保存至: {output_file}")

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except json.JSONDecodeError:
        print(f"错误：文件 {input_file} 不是有效的 JSON 格式")
    except Exception as e:
        print(f"发生未知错误: {e}")

# ================= 配置区域（基于项目相对路径）=================

input_filename = os.path.join(_PROJECT_ROOT, 'generate_data', 'delivery', 'Del-sys', 'agent_system_prompt_final', 'agent_system_prompt_attack_tasks.json')
output_filename = os.path.join(_PROJECT_ROOT, 'generate_data', 'delivery', 'Del-sys', 'agent_system_prompt_final', 'claude_tasks2.json')

# 在这里指定你要保留的 ID (请根据你文件实际的 ID 类型是 字符串 还是 整数 进行修改)
# # 示例：假设 ID 是整数
# ids_to_keep = [1, 5, 12, 33, 48] 

# 如果 ID 是字符串，请使用引号，例如：
ids_to_keep = ["C0715001_B_Law-18_user_direct_Law-18","H0721003_other_backdoor_Shopping_Fraud-16"]

# ===========================================

if __name__ == "__main__":
    filter_json_by_ids(input_filename, output_filename, ids_to_keep)
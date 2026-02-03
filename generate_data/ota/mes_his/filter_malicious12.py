import json
import os

def filter_json_data(input_file, output_file):
    # 筛选关键词列表
    target_keywords = ["Privacy-6", "Authority-7", "Finance-9", "Law-17", "Law-18"]
    
    # 目标最大数量
    target_count = 12
    
    filtered_data = []

    try:
        # 1. 读取源文件
        with open(input_file, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
            
        # 确保源数据是一个列表
        if not isinstance(source_data, list):
            print("错误：源 JSON 文件必须包含一个对象列表。")
            return

        # 2. 按顺序遍历筛选
        for item in source_data:
            # 检查是否已达到目标数量
            if len(filtered_data) >= target_count:
                break
            
            # 获取 id 字段
            item_id = item.get('id', '')
            
            # 检查 id 是否包含任意一个目标关键词
            # 使用 any() 函数来判断 item_id 中是否包含 target_keywords 中的任意一个字符串
            if any(keyword in item_id for keyword in target_keywords):
                filtered_data.append(item)

        # 3. 写入新文件
        with open(output_file, 'w', encoding='utf-8') as f:
            # ensure_ascii=False 保证中文字符（如果有）正常显示
            # indent=4 保证输出格式美观
            json.dump(filtered_data, f, ensure_ascii=False, indent=4)

        print(f"筛选完成！")
        print(f"共找到 {len(filtered_data)} 条符合条件的数据。")
        print(f"结果已保存至: {output_file}")

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except json.JSONDecodeError:
        print(f"错误：文件 {input_file} 不是有效的 JSON 格式")
    except Exception as e:
        print(f"发生未知错误: {e}")

# --- 配置部分（相对于 bench 项目根）---
if __name__ == "__main__":
    _ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    source_filename = os.path.join(_ROOT, "data", "vita", "domains", "ota", "task_en_ota_usr_ins_process.json")
    output_filename = os.path.join(_ROOT, "data", "vita", "generator_prompt", "Ota-User", "message_history", "tasks_ui_en_simple12.json")
    filter_json_data(source_filename, output_filename)
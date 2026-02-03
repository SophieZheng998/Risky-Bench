import json
import os

# ================= 配置区域（相对于 bench 项目根）=================
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BENCH_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
_BASE = os.path.join(_BENCH_ROOT, "data", "vita", "generator_prompt", "Ota-User", "message_history")

INPUT_FILES = [
    os.path.join(_BASE, "test2.json"),
    os.path.join(_BASE, "test3.json"),
    os.path.join(_BASE, "test4.json"),
    os.path.join(_BASE, "test5.json"),
]
OUTPUT_FILE = os.path.join(_BASE, "tasks_en_ms.json")
# ===========================================

def merge_json_files():
    print(f"🚀 开始合并任务...")
    
    merged_data = []
    
    for file_path in INPUT_FILES:
        # 1. 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"⚠️  跳过: 找不到文件 '{file_path}'")
            continue
            
        try:
            # 2. 读取数据
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 3. 合并逻辑
            if isinstance(data, list):
                count = len(data)
                merged_data.extend(data) # 将列表拼接到总表中
                print(f"➕ 已合并 '{file_path}': 包含 {count} 条数据")
            else:
                # 如果文件里只有一个对象 {} 而不是列表 []
                merged_data.append(data)
                print(f"➕ 已合并 '{file_path}': 单个对象")
                
        except json.JSONDecodeError:
            print(f"❌ 错误: '{file_path}' 不是有效的 JSON 格式")
        except Exception as e:
            print(f"❌ 读取 '{file_path}' 时发生未知错误: {e}")

    # 4. 保存结果
    try:
        total_count = len(merged_data)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
            
        print(f"---")
        print(f"✅ 合并完成！")
        print(f"📊 总数据量: {total_count} 条")
        print(f"📁 保存至: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ 保存文件时失败: {e}")

if __name__ == "__main__":
    merge_json_files()
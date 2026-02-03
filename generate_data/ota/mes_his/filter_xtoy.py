import json
import os

# ================= 配置区域（相对于 bench 项目根）=================
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BENCH_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
INPUT_FILE = os.path.join(_BENCH_ROOT, "data", "vita", "domains", "ota", "tasks_en_process.json")
OUTPUT_FILE = os.path.join(_BENCH_ROOT, "data", "vita", "generator_prompt", "Ota-User", "message_history", "tasks_normal_en_simple12.json")

START_X = 26   # 从第几条开始 (包含)
END_Y   = 37   # 到第几条结束 (包含)
# ===========================================

def run_extraction():
    """
    执行提取逻辑
    """
    print(f"🚀 开始处理...")
    
    # 1. 检查文件
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误: 找不到输入文件 '{INPUT_FILE}'")
        return

    try:
        # 2. 读取
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("❌ 错误: JSON 根对象必须是列表 []")
            return

        total_count = len(data)
        print(f"ℹ️  读取成功，源文件共有 {total_count} 个对象。")

        # 3. 计算切片索引 (转换为 Python 的 0-based 索引)
        # 用户输入 1 -> Python index 0
        slice_start = START_X - 1
        # 用户输入 10 -> Python slice end 10 (包含 index 9)
        slice_end = END_Y

        # 边界保护
        if slice_start < 0: slice_start = 0
        if slice_end > total_count: slice_end = total_count

        if slice_start >= slice_end:
            print(f"❌ 错误: 范围无效 (第 {START_X} 到 {END_Y} 条)")
            return

        # 4. 提取
        subset = data[slice_start:slice_end]
        extract_count = len(subset)

        # 5. 保存
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(subset, f, ensure_ascii=False, indent=4)

        print(f"---")
        print(f"✅ 成功提取: 第 {START_X} 到 {END_Y} 条")
        print(f"📊 实际保存: {extract_count} 条数据")
        print(f"📁 文件位置: {OUTPUT_FILE}")

    except json.JSONDecodeError:
        print("❌ 错误: JSON 格式损坏")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    run_extraction()
# Riskybench 数据生成

本目录提供 Riskybench 的数据生成脚本。若你希望复现或扩展实验，可以在此目录下根据文档运行脚本，自行生成各领域、各攻击面的评测数据。

---

## 目录

- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [运行方式](#运行方式)
- [目录结构](#目录结构)
- [输出说明](#输出说明)
- [常见问题](#常见问题)
- [更多文档](#更多文档)

---

## 环境要求

我是在以下环境中开发和测试的，建议读者尽量一致，以减少环境差异带来的问题：

| 项目     | 要求                    |
|----------|-------------------------|
| 操作系统 | Linux（推荐 Ubuntu 20.04+） |
| Python   | 3.10+                   |
| 依赖     | `openai` 等（见项目根目录 `requirements.txt` 或 `pyproject.toml`） |

请先在**项目根目录**（即包含 `generate_data/` 的那一层）安装依赖，例如：

```bash
pip install -e .
# 或
pip install -r requirements.txt
```

---

## 快速开始

1. **进入项目根目录**（重要：脚本中的路径是相对于项目根解析的）

   ```bash
   cd <your-project-root>
   ```

2. **配置运行时环境变量**（本仓库为匿名提交版本，文档不包含任何密钥示例；请在本地自行设置）

   需要的变量名称通常包括：`API_KEY`、`MODEL_NAME`，以及可选的 `BASE_URL`（具体以各脚本读取逻辑为准）。

3. **准备原始数据**  
   请确保对应领域下已有英文任务文件（如 `data/vita/domains/<domain>/tasks_en.json`）。若仓库中已提供示例或占位文件，可直接使用；否则需要先按各领域说明准备输入。

4. **运行一次最小生成（建议先试跑）**  
   以下每条命令为对应领域生成 **1 个任务**，便于快速检查环境与 API 是否正常：

   ```bash
   # Delivery
   bash generate_data/delivery/run_generate.sh \
     ./data/vita/domains/delivery/tasks_en.json 0 1 ./data/vita/domains/delivery/

   # OTA（仅 ui 攻击面）
   bash generate_data/ota/run_generate.sh \
     ./data/vita/domains/ota/tasks_en.json 0 1 ./data/vita/domains/ota/ ui

   # Instore
   bash generate_data/instore/run_generate.sh \
     ./data/vita/domains/instore/tasks_en.json 0 1 ./data/vita/domains/instore/
   ```

   若输出目录下出现对应的 `*_1_en.json` 且无报错，说明环境与配置正确，可以再按需增大任务数量或切换攻击面。

---

## 配置说明

脚本通过环境变量读取配置。为避免匿名仓库出现任何密钥或可追溯信息，本 README 不展示具体取值示例；如遇 404 等报错，请重点核对 `BASE_URL` 仅为基础地址（一般到 `/v1`）。

---

## 运行方式

所有领域的入口均为各子目录下的 `run_generate.sh`，统一参数格式如下：

```bash
bash generate_data/<领域>/run_generate.sh <original_file> <start_idx> <number_of_tasks> <output_path> [攻击面]
```

| 参数             | 说明 |
|------------------|------|
| `original_file`  | 原始英文任务文件路径（相对或绝对均可）。 |
| `start_idx`      | 起始任务下标（从 0 开始）。 |
| `number_of_tasks`| 要生成的任务数量。 |
| `output_path`    | 结果输出目录（建议使用相对路径，如 `./data/vita/domains/<领域>/`）。 |
| `攻击面`         | **仅 OTA 领域**支持：`ui` / `env` / `tf` / `ms` / `sys` / `all`，默认 `all`。其他领域忽略此参数。 |

### 示例：按领域与攻击面

**Delivery**（ui / env / ms）：

```bash
bash generate_data/delivery/run_generate.sh \
  ./data/vita/domains/delivery/tasks_en.json \
  0 10 \
  ./data/vita/domains/delivery/
```

**OTA**（可指定单攻击面或全部）：

```bash
# 全部攻击面
bash generate_data/ota/run_generate.sh \
  ./data/vita/domains/ota/tasks_en.json 0 10 ./data/vita/domains/ota/

# 仅 ui
bash generate_data/ota/run_generate.sh \
  ./data/vita/domains/ota/tasks_en.json 0 10 ./data/vita/domains/ota/ ui
```

**Instore**（ui / tf / sys）：

```bash
bash generate_data/instore/run_generate.sh \
  ./data/vita/domains/instore/tasks_en.json \
  0 10 \
  ./data/vita/domains/instore/
```

---

## 目录结构

便于读者对照仓库与文档，当前结构大致如下（仅列出与数据生成直接相关的部分）：

```
generate_data/
├── README.md                 # 本说明
├── delivery/                 # Delivery 领域
│   ├── run_generate.sh       # 统一入口
│   ├── run_generate.py
│   ├── Delivery-User/        # user_instruction (ui)
│   ├── Delivery-Environmental/  # env_noise (env)
│   ├── Del-mem/              # message_history (ms)
│   └── ...
├── ota/                      # OTA 领域
│   ├── run_generate.sh
│   ├── generate_user_ins_en_tasks.py   # ui
│   ├── generate_tasks_env_indirect_ota.py  # env
│   ├── generate_tasks_tf_ota.py   # tf
│   ├── generate_tasks_ms_ota.py  # ms
│   ├── generate_tasks_sys_ota.py # sys
│   ├── mes_his/
│   ├── sys/
│   └── README.md
└── instore/                  # Instore 领域
    ├── run_generate.sh
    ├── ui/   # user_instruction
    ├── tf/   # tool_feedback
    ├── sys/  # system_prompt
    └── ms/   # message_history
```

生成结果会写入你指定的 `output_path`，通常我们约定放在 `data/vita/domains/<领域>/` 下，脚本不会自动创建项目根以外的目录，请先保证输出路径存在或脚本有写权限。

---

## 输出说明

- **文件名格式**：`{领域}_{攻击面}_{任务数}_en.json`  
  例如：`delivery_ui_10_en.json`、`ota_sys_5_en.json`。
- **攻击面缩写**：  
  `ui` = user_instruction，`env` = env_noise，`tf` = tool_feedback，`ms` = message_history，`sys` = system_prompt。
- **输出路径**：完全由你在命令行中传入的 `output_path` 决定；若目录不存在，部分脚本会尝试创建，具体以各领域实现为准。

---

## 常见问题

1. **API 返回 404**  
   请检查 `BASE_URL` 是否只填到基础地址 + `/v1`，没有包含 `/chat/completions`。

2. **找不到输入文件**  
   请确认在 **项目根目录** 下执行命令，且 `original_file` 路径正确；若使用相对路径，是相对于当前工作目录（建议即为项目根）。

3. **依赖报错**  
   请在项目根目录安装依赖（如 `pip install -e .` 或 `pip install -r requirements.txt`），并确认 Python 版本 ≥ 3.10。

4. **只想快速验证**  
   使用「快速开始」中的最小生成命令（任务数设为 1），检查是否生成 `*_1_en.json` 且无报错。

---

## 更多文档

- **Delivery**： [delivery/README.md](delivery/README.md)
- **OTA**： [ota/README.md](ota/README.md)  
- **Instore**： 无单独 README，入口为 `instore/run_generate.sh`，支持 ui / tf / sys。

若你在使用中遇到脚本错误，请在本项目内部记录复现方式与报错信息，便于排查。

# 🍜 嗨，这道菜 · AI 美食识别与食谱推荐

> 拍一张美食照片，认出它叫什么，并顺手推荐这道菜的做法。

一个基于 **计算机视觉（CV）+ 自然语言处理（NLP）** 的端到端美食应用：用 EfficientNet-B3 在 Food-101（101 类）上做细粒度图像识别，再用 Sentence-BERT 语义检索从 200 万+ 条食谱里匹配最贴合的做法，最后用 FastAPI 提供 Web 服务，前端是一套自包含的暖色「点评 / 小红书」风界面。

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

---

## ✨ 功能特性

- 📷 **拍照 / 拖拽 / Ctrl+V 粘贴** 上传图片，识别 101 类美食
- ⭐ 识别把握度用**星级**展示，并给出 **Top-5 候选**
- 📖 **语义检索推荐食谱**（用料 + 步骤），而非关键词硬匹配
- 🌐 一键**中文翻译**食谱（百度通用翻译 API，含前端串行限流）
- 🛒 食材**一键跳转淘宝**搜索
- 📱 **响应式**前端，暖色食欲系配色，移动端顺滑

## 🧱 技术栈

| 层 | 技术 |
| :-- | :-- |
| 图像识别 | PyTorch, torchvision（EfficientNet-B3，迁移学习） |
| 食谱检索 | Sentence-Transformers（all-MiniLM-L6-v2）, scikit-learn（余弦相似度） |
| 后端服务 | FastAPI, Uvicorn |
| 前端 | 原生 HTML5 / CSS3 / JavaScript（无框架、单文件自包含） |
| 翻译 | 百度通用翻译 API |

## 📊 实验结果

| 数据集 | 样本规模 | Top-1 准确率 |
| :-- | :-- | :-- |
| Food-101 验证集 | 25,250 | **80.05%** |
| 真实网络图片（爬虫盲测） | 520 | **78.46%** |

> 在完全非受控的网络图片上性能仅下降约 1.6%，说明模型有较强的鲁棒性。详见 [`experiment_report.md`](experiment_report.md)。

## 📁 项目结构

```
.
├── app.py                     # FastAPI 后端：/predict 推理 + /translate 翻译
├── static/
│   └── index.html             # 前端单页（自包含，含 101 道菜中文名/简介）
├── train_efficientnet.py      # EfficientNet-B3 训练脚本
├── preprocess_food101.py      # Food-101 数据预处理
├── preprocess_recipes.py      # RecipeNLG 文本清洗 + 向量化
├── match_recipes.py           # 语义检索，生成 final_recipes.json
├── predict.py                 # 命令行单图预测
├── evaluate_model.py          # 模型评估
├── plot_accuracy.py           # 准确率可视化
├── scrape_images.py           # 真实场景测试集爬虫
├── requirements.txt
├── experiment_report.md       # 完整实验报告
└── README.md
```

> 说明：模型权重、数据集、检索库等大文件**未包含**在仓库中（见下方「准备模型与数据」）。

## 🚀 快速开始

### 1. 安装依赖

推荐 Python 3.8+（实测 3.11 可用）：

```bash
pip install -r requirements.txt
```

> 仅运行 Web 服务时，核心依赖是 `fastapi / uvicorn / torch / torchvision / pillow / requests / pydantic / python-multipart`；`requirements.txt` 里其余包（sentence-transformers、pandas、scikit-learn、matplotlib 等）用于**训练与数据预处理**。
> CPU 环境安装 PyTorch 可用 CPU 版索引：`pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`

### 2. 准备模型与数据（仓库不含大文件）

请自行准备以下文件并放到对应位置：

| 文件 | 放置位置 | 说明 |
| :-- | :-- | :-- |
| `best_efficientnet_b3_food101.pth` | 项目根目录 | 训练得到的模型权重（用 `train_efficientnet.py` 训练） |
| `classes.txt` | `food-101/meta/classes.txt` | Food-101 的 101 个类别表 |
| `final_recipes.json` | `recipes/final_recipes.json` | 预计算的检索库（用 `match_recipes.py` 生成） |

> Food-101 数据集：<https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/>
> RecipeNLG 数据集：<https://recipenlg.cs.put.poznan.pl/>

### 3. 配置百度翻译密钥（可选）

代码从**环境变量**读取密钥，不在仓库中保存明文。不配置也能正常识别，只是「翻译」功能不可用。

```bash
# Windows (PowerShell)
$env:BAIDU_APP_ID="你的AppID"; $env:BAIDU_APP_KEY="你的Key"

# Linux / macOS
export BAIDU_APP_ID=你的AppID BAIDU_APP_KEY=你的Key
```

> 百度翻译开放平台申请：<https://fanyi-api.baidu.com/>

### 4. 启动

```bash
python app.py
# 或（生产）：
uvicorn app:app --host 0.0.0.0 --port 8000
```

浏览器打开 <http://localhost:8000> 即可使用。

## 🌐 部署参考（Linux + systemd）

```ini
# /etc/systemd/system/food_app.service
[Unit]
Description=Food Recognition Web App
After=network.target

[Service]
WorkingDirectory=/opt/food_app
Environment=BAIDU_APP_ID=你的AppID
Environment=BAIDU_APP_KEY=你的Key
ExecStart=/opt/food_app/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now food_app
```

> 公网访问记得在云厂商**安全组**放行对应端口。

## 📝 说明与许可

- Food-101、RecipeNLG 等数据集版权归各自原作者所有，本仓库不分发数据集本体。
- 本项目为学习 / 课程作业用途，仅供交流参考。

---

<sub>识别结果不一定全对，当个有趣的参考就好 🙂</sub>

"""
RecipeNLG 预处理脚本
====================

功能描述：
1. 读取 Food-101 的 101 个类别名称（从 meta/classes.txt）。
2. 生成类别的关键词变体（如 "apple_pie" -> "apple pie", "apple-pie" 等），并支持自定义扩充（如中文关键词）。
3. 分块读取大规模 RecipeNLG_dataset.csv 数据集。
4. 对每条食谱进行文本拼接（标题 + 食材 + 步骤）。
5. 基于关键词筛选属于 Food-101 类别的食谱。
6. 使用 Sentence-BERT 模型将食谱文本编码为固定长度的语义向量。
7. 将结果按类别保存为 JSONL 文件，支持断点续跑和自动去重。

输出路径：
- recipes/embeddings/<class_name>.jsonl

依赖库：
- pandas: 数据处理
- sentence-transformers: 文本向量化模型
- torch: 深度学习框架后端
- tqdm: 进度条显示
"""

from pathlib import Path
from typing import Dict, List, Iterable, Optional
import hashlib
import json
import re
import os

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer


def read_classes(base_dir: Path) -> List[str]:
    """
    读取 Food-101 数据集的类别列表。
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        包含 101 个类别名称的字符串列表
    """
    classes_txt = base_dir / "food-101" / "meta" / "classes.txt"
    # 读取文件，去除空行和首尾空格
    classes = [l.strip() for l in classes_txt.read_text(encoding="utf-8").splitlines() if l.strip()]
    return classes


def generate_keyword_variants(cls: str) -> List[str]:
    """
    为给定的类别名称生成常见的英文拼写变体。
    例如：'apple_pie' -> ['apple_pie', 'apple pie', 'apple-pie', 'applepie']
    
    Args:
        cls: 原始类别名称（通常带下划线）
        
    Returns:
        包含该类别所有拼写变体的列表
    """
    base = cls.lower()
    space = base.replace("_", " ")    # 将下划线替换为空格
    hyphen = base.replace("_", "-")   # 将下划线替换为连字符
    tight = base.replace("_", "")     # 去除下划线（紧凑模式）
    variants = {base, space, hyphen, tight}
    return list(variants)


def load_custom_keywords(base_dir: Path) -> Dict[str, List[str]]:
    """
    加载用户自定义的关键词映射文件（recipes/class_keywords.json）。
    主要用于添加中文关键词或特定同义词。
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        字典，键为类别名，值为额外的关键词列表
    """
    cfg = base_dir / "recipes" / "class_keywords.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            # 确保所有关键词转换为小写，便于后续匹配
            return {k.lower(): [x.lower() for x in v] for k, v in data.items()}
        except Exception:
            return {}
    return {}


def build_class_keywords(base_dir: Path) -> Dict[str, List[str]]:
    """
    构建最终的类别-关键词映射表。
    合并了自动生成的变体和用户自定义的关键词。
    
    Returns:
        字典：{ 'apple_pie': ['apple pie', 'apple-pie', ...], ... }
    """
    classes = read_classes(base_dir)
    custom = load_custom_keywords(base_dir)
    keywords: Dict[str, List[str]] = {}
    for cls in classes:
        variants = generate_keyword_variants(cls)
        # 如果有自定义关键词（如中文名），则合并进来
        if cls.lower() in custom:
            variants.extend(custom[cls.lower()])
        # 去重并排序
        keywords[cls] = sorted(list({v.lower() for v in variants}))
    return keywords


def _safe_get(row: pd.Series, candidates: Iterable[str]) -> Optional[str]:
    """
    从 pandas 行中安全获取数据，尝试多个可能的列名。
    解决不同版本 CSV 列名不一致的问题。
    """
    for c in candidates:
        if c in row and pd.notna(row[c]):
            return str(row[c])
    return None


def normalize_list_text(val: Optional[str]) -> str:
    """
    规范化列表格式的文本字段。
    有些 CSV 字段可能是 "['salt', 'sugar']" 这样的字符串，需要转换成 "salt, sugar"。
    """
    if val is None:
        return ""
    s = str(val)
    s_strip = s.strip()
    # 尝试解析 JSON 格式的列表字符串
    if (s_strip.startswith("[") and s_strip.endswith("]")) or (s_strip.startswith("(") and s_strip.endswith(")")):
        try:
            # 替换圆括号以兼容 Python tuple 字符串格式
            obj = json.loads(s_strip.replace("(", "[").replace(")", "]"))
            if isinstance(obj, (list, tuple)):
                return ", ".join(map(str, obj))
        except Exception:
            pass
    return s


def build_text(row: pd.Series) -> str:
    """
    将一行数据拼接成完整的待编码文本。
    格式：
    [Title]
    Ingredients: [List]
    Directions: [List]
    """
    title = _safe_get(row, ["title", "name", "recipe_title", "Recipe_title"]) or ""
    ing = normalize_list_text(_safe_get(row, ["ingredients", "ingredient", "Ingredients", "ingredients_list"]))
    steps = normalize_list_text(_safe_get(row, ["directions", "instructions", "Steps", "steps"]))
    text = f"{title}\nIngredients: {ing}\nDirections: {steps}"
    return text


def find_class_match(text_lower: str, class_keywords: Dict[str, List[str]]) -> Optional[str]:
    """
    在文本中查找匹配的类别。
    采用简单的包含匹配：如果文本包含某类别的任意关键词，则认为属于该类。
    """
    for cls, kws in class_keywords.items():
        for kw in kws:
            if kw and kw in text_lower:
                return cls
    return None


def ensure_dir(p: Path):
    """确保目录存在，不存在则创建"""
    p.mkdir(parents=True, exist_ok=True)


def filter_and_encode(
    base_dir: Path,
    csv_path: Path,
    output_dir: Path,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    batch_size: int = 64,
    chunksize: int = 50000,
    limit_per_class: Optional[int] = None,
    resume: bool = False,
    deduplicate: bool = True,
):
    """
    核心处理函数：筛选并编码食谱数据。
    
    Args:
        base_dir: 项目根目录
        csv_path: RecipeNLG CSV 文件路径
        output_dir: 结果输出目录
        model_name: Sentence-BERT 模型名称
        batch_size: 编码时的批次大小
        chunksize: 读取 CSV 时的分块大小（避免内存溢出）
        limit_per_class: 每个类别的最大样本数（可选，用于测试或平衡数据）
        resume: 是否开启断点续跑（True: 不覆盖旧文件，追加新数据）
        deduplicate: 是否开启去重（True: 基于文本哈希去重）
        
    Returns:
        字典，记录每个类别已保存的样本数量
    """
    # 1. 准备关键词和输出目录
    class_keywords = build_class_keywords(base_dir)
    ensure_dir(output_dir)

    # 2. 加载 Sentence-BERT 模型
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading model '{model_name}' on device: {device}...")
    model = SentenceTransformer(model_name, device=device)

    # 3. 初始化计数器和状态
    kept_counts: Dict[str, int] = {cls: 0 for cls in class_keywords}
    existing_keys: Dict[str, set] = {cls: set() for cls in class_keywords}

    # 4. 准备输出文件句柄
    writers: Dict[str, Path] = {cls: (output_dir / f"{cls}.jsonl") for cls in class_keywords}
    
    # 初始化文件状态（处理断点续跑）
    for cls, p in writers.items():
        if p.exists():
            if not resume:
                p.unlink()  # 如果不续跑，删除旧文件
            else:
                # 如果续跑，读取已有的数据以恢复计数和去重集合
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                obj = json.loads(line)
                                kept_counts[cls] += 1
                                if deduplicate:
                                    # 重新计算哈希值以避免重复
                                    title = obj.get("title", "")
                                    ingredients = obj.get("ingredients", "")
                                    directions = obj.get("directions", "")
                                    text = f"{title}\nIngredients: {ingredients}\nDirections: {directions}"
                                    key = hashlib.sha1(text.lower().encode("utf-8")).hexdigest()
                                    existing_keys[cls].add(key)
                            except Exception:
                                continue
                except Exception:
                    pass

    # 5. 分块读取 CSV 并处理
    # 尝试不同的编码格式以应对潜在的乱码问题
    read_ok = False
    encodings_to_try = ["utf-8", "latin-1"]
    
    for enc in encodings_to_try:
        try:
            print(f"Reading CSV with encoding: {enc}, chunksize: {chunksize}...")
            # pandas.read_csv 的 chunksize 参数返回一个迭代器，每次返回一个 DataFrame 块
            for chunk in pd.read_csv(csv_path, encoding=enc, chunksize=chunksize):
                rows_text: List[str] = []
                rows_meta: List[Dict] = []
                
                # 遍历当前块中的每一行
                for _, row in chunk.iterrows():
                    # 构建完整文本
                    text = build_text(row)
                    t_lower = text.lower()
                    
                    # 匹配类别
                    cls = find_class_match(t_lower, class_keywords)
                    if cls is None:
                        continue # 未匹配到任何类别
                    
                    # 检查数量限制
                    if limit_per_class is not None and kept_counts[cls] >= limit_per_class:
                        continue
                    
                    # 生成去重键（SHA1哈希）
                    key = hashlib.sha1(t_lower.encode("utf-8")).hexdigest() if deduplicate else None
                    
                    # 检查重复
                    if deduplicate and key in existing_keys[cls]:
                        continue
                    
                    # 添加到待编码列表
                    rows_text.append(text)
                    rows_meta.append({
                        "class": cls,
                        "title": _safe_get(row, ["title", "name", "recipe_title", "Recipe_title"]) or "",
                        "ingredients": _safe_get(row, ["ingredients", "ingredient", "Ingredients", "ingredients_list"]) or "",
                        "directions": _safe_get(row, ["directions", "instructions", "Steps", "steps"]) or "",
                        "key": key,
                        "row_index": int(getattr(row, "name", -1)),
                    })

                if not rows_text:
                    continue

                # 打印当前块的匹配情况
                print(f"Chunk matched samples: {len(rows_text)}. Encoding…")

                # 6. 批量编码（耗时步骤）
                embeddings = model.encode(
                    rows_text,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=True,  # 显示进度条
                    normalize_embeddings=False,
                )

                # 7. 将结果写入文件
                for meta, emb in zip(rows_meta, embeddings):
                    cls = meta["class"]
                    out = {
                        "class": cls,
                        "title": meta["title"],
                        "ingredients": meta["ingredients"],
                        "directions": meta["directions"],
                        "embedding": emb.tolist(),  # 转换为列表以便 JSON 序列化
                    }
                    
                    # 更新去重集合
                    if deduplicate:
                        out["key"] = meta.get("key")
                        if out["key"]:
                            existing_keys[cls].add(out["key"])
                    
                    # 如果文件不存在则创建（确保为空文件先写入）
                    if not writers[cls].exists():
                         writers[cls].write_text("", encoding="utf-8")
                    
                    # 追加写入一行 JSON 数据
                    with open(writers[cls], "a", encoding="utf-8") as f:
                        f.write(json.dumps(out, ensure_ascii=False) + "\n")
                    
                    kept_counts[cls] += 1

                # 打印累计进度
                print(f"Chunk done. Total kept so far: {sum(kept_counts.values())}")

            read_ok = True
            break # 成功读取完毕，跳出编码尝试循环
        except Exception as e:
            print(f"Error reading with encoding {enc}: {e}")
            continue

    if not read_ok:
        raise RuntimeError("无法读取 RecipeNLG_dataset.csv，请检查文件编码或结构。")

    return kept_counts


if __name__ == "__main__":
    # 设置路径
    base = Path(__file__).resolve().parent
    csv_path = base / "recipes" / "RecipeNLG_dataset.csv"
    out_dir = base / "recipes" / "embeddings"

    print("Building class keywords…")
    
    # 执行处理
    kept = filter_and_encode(
        base_dir=base,
        csv_path=csv_path,
        output_dir=out_dir,
        model_name="sentence-transformers/all-MiniLM-L6-v2", # 使用的模型
        batch_size=64,             # 编码批大小，显存不足可调小
        chunksize=50000,           # CSV 读取分块大小
        limit_per_class=None,      # 设为数字可限制每类样本数（如 2000）
        resume=True,               # 开启断点续跑
        deduplicate=True,          # 开启去重
    )
    
    print("Done. Per-class counts:")
    for k, v in sorted(kept.items()):
        print(f"{k}: {v}")

"""
食谱语义匹配脚本 (Semantic Matching)

功能描述：
1. 加载 Food-101 的 101 个类别名称。
2. 使用 Sentence-BERT (all-MiniLM-L6-v2) 对类别名称进行编码。
3. 读取 `preprocess_recipes.py` 生成的食谱嵌入文件 (recipes/embeddings/*.jsonl)。
4. 计算 "类别向量" 与 "食谱向量" 的余弦相似度。
5. 为每个类别筛选相似度最高的 Top-10 食谱。
6. 将最终匹配结果保存为 JSON 文件，供后续应用查询。
7. 检查食谱数量不足 10 条的类别，并提示需要扩展关键词。

输入路径：
- recipes/embeddings/<class_name>.jsonl (包含预计算的 embedding)

输出路径：
- recipes/final_recipes.json (最终的 Top-10 结果)
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from tqdm import tqdm

def load_classes(base_dir: Path) -> List[str]:
    """读取类别列表"""
    classes_txt = base_dir / "food-101" / "meta" / "classes.txt"
    return [l.strip() for l in classes_txt.read_text(encoding="utf-8").splitlines() if l.strip()]

def load_candidates(jsonl_path: Path) -> List[Dict]:
    """
    读取 JSONL 文件中的候选食谱及其 Embedding。
    
    Args:
        jsonl_path (Path): .jsonl 文件路径，每行是一个包含食谱信息和 embedding 的 JSON 对象。
        
    Returns:
        List[Dict]: 包含食谱数据的字典列表。如果文件不存在或解析失败，返回空列表。
    """
    candidates = []
    if not jsonl_path.exists():
        return candidates
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                # 逐行解析 JSON 数据
                data = json.loads(line)
                candidates.append(data)
            except json.JSONDecodeError:
                # 忽略格式错误的行，防止程序中断
                continue
    return candidates

def match_and_rank(
    model: SentenceTransformer,
    classes: List[str],
    embeddings_dir: Path,
    top_k: int = 10
) -> Dict[str, List[Dict]]:
    """
    核心匹配逻辑：计算类别与食谱的语义相似度，并筛选 Top-K。
    
    Args:
        model: 预训练的 SentenceTransformer 模型
        classes: Food-101 类别名称列表
        embeddings_dir: 存放预处理后食谱 embedding 的目录
        top_k: 每个类别保留的食谱数量 (默认 10)
        
    Returns:
        Dict: 键为类别名，值为匹配到的食谱列表 (包含 title, ingredients, directions, score)
    """
    results = {}
    insufficient_classes = []

    print(f"正在为 {len(classes)} 个类别匹配最佳食谱...")

    # 1. 编码所有类别名称 (一次性编码，速度快)
    # 预处理：将类别名称中的下划线替换为空格 (e.g., "apple_pie" -> "apple pie")
    # 这样可以让 Sentence-BERT 更好地理解语义，因为 BERT 模型是在自然语言文本上训练的
    class_texts = [c.replace("_", " ") for c in classes]
    
    # 使用模型将所有类别名称转换为向量 (Embeddings)
    # convert_to_tensor=True 返回 PyTorch Tensor，方便后续在 GPU/CPU 上进行矩阵运算
    class_embeddings = model.encode(class_texts, convert_to_tensor=True)

    # 2. 遍历每个类别进行匹配
    for idx, cls_name in enumerate(tqdm(classes)):
        cls_embedding = class_embeddings[idx] # 获取当前类别的向量，Shape: [384]
        
        # 加载该类别的候选食谱 (由 preprocess_recipes.py 生成)
        jsonl_path = embeddings_dir / f"{cls_name}.jsonl"
        candidates = load_candidates(jsonl_path)
        
        # 如果该类别没有候选食谱，记录并跳过
        if not candidates:
            results[cls_name] = []
            insufficient_classes.append((cls_name, 0))
            continue
            
        # 提取候选食谱的 embedding
        # 注意：JSON 中读取的 embedding 是 List[float]，需要转换为 PyTorch Tensor 才能进行 GPU 加速计算
        cand_embeddings = [c["embedding"] for c in candidates]
        cand_embeddings_tensor = torch.tensor(cand_embeddings).to(model.device)
        
        # 计算余弦相似度 (Cosine Similarity)
        # cls_embedding 是当前类别的向量
        # cand_embeddings_tensor 是所有候选食谱的向量矩阵
        # util.cos_sim 计算两个张量之间的余弦相似度，返回结果 shape 为 [1, N]
        # 我们取 [0] 得到一个包含 N 个相似度分数的 1D Tensor
        cos_scores = util.cos_sim(cls_embedding, cand_embeddings_tensor)[0]
        
        # 获取 Top-K 索引
        # torch.topk 返回两个 tensor: values (分数) 和 indices (原始索引)
        # 如果候选数量少于 top_k，则取全部候选
        k = min(top_k, len(candidates))
        top_results = torch.topk(cos_scores, k=k)
        
        # 构建结果列表
        matched_recipes = []
        for score, item_idx in zip(top_results.values, top_results.indices):
            item = candidates[item_idx.item()]
            matched_recipes.append({
                "title": item["title"],
                "ingredients": item["ingredients"],
                "directions": item["directions"],
                "score": float(score) # 将 Tensor 转为 Python float，确保 JSON 可序列化
            })
            
        results[cls_name] = matched_recipes
        
        # 记录候选数量不足的情况
        if len(matched_recipes) < top_k:
            insufficient_classes.append((cls_name, len(matched_recipes)))

    # 打印警告信息，提示用户可能需要改进关键词搜索
    if insufficient_classes:
        print("\n⚠️  以下类别食谱数量不足 10 条，建议扩展关键词重新运行预处理：")
        for cls, count in insufficient_classes:
            print(f"  - {cls}: {count} 条")
    else:
        print("\n✅ 所有类别均找到足够的匹配食谱。")

    return results

def main():
    # 设置基础路径
    base_dir = Path(__file__).resolve().parent
    embeddings_dir = base_dir / "recipes" / "embeddings"
    output_path = base_dir / "recipes" / "final_recipes.json"
    
    # 检查输入目录是否存在
    if not embeddings_dir.exists():
        print(f"错误: 找不到嵌入向量目录 {embeddings_dir}")
        print("请先运行 preprocess_recipes.py 生成数据。")
        return

    # 加载 Sentence-BERT 模型
    # 使用 "all-MiniLM-L6-v2": 速度快，效果好，生成 384 维向量
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"正在加载模型: {model_name} ...")
    model = SentenceTransformer(model_name)
    
    # 加载 Food-101 类别列表
    classes = load_classes(base_dir)
    
    # 执行语义匹配和排序
    final_data = match_and_rank(model, classes, embeddings_dir, top_k=10)
    
    # 保存最终结果
    print(f"正在保存结果到: {output_path} ...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        # ensure_ascii=False 保证中文字符（如果有）正常显示，indent=2 美化输出
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print("完成！")

if __name__ == "__main__":
    main()


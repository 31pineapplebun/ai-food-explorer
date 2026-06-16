"""
Food-101 数据预处理与加载

功能概述：
- 图像尺寸统一：默认 Resize 到 224×224（你可改为 300×300 以匹配 EfficientNet-B3 推荐尺寸）
- 归一化：使用 ToTensor() 将像素值缩放到 [0,1]
- 数据增强：训练集应用随机水平翻转、旋转、颜色抖动等
- 数据划分：从官方 train.txt 按类别分层抽取 10% 作为验证集，保存到 meta/val.txt
- 数据接口：提供 PyTorch Dataset 与 DataLoader 用于 train/val/test 三分

分辨率选择建议：
- 使用 EfficientNet-B3 预训练权重时，推荐 300×300（更高准确率，显存与算力开销更大）
- 若算力/显存有限或需更快训练，可使用 224×224（速度更快、精度略降）
你可以在 get_transforms(image_size=...) 或 get_dataloaders(...) 调用处改为 300。
"""

from pathlib import Path
import random
from typing import List, Tuple, Dict

from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms


def _read_lines(path: Path) -> List[str]:
    """读取文本文件的非空行，去除首尾空白。"""
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _build_class_map(classes_txt: Path) -> Dict[str, int]:
    """根据 classes.txt 构建类别到索引的映射。"""
    classes = _read_lines(classes_txt)
    return {cls_name: idx for idx, cls_name in enumerate(classes)}


def _parse_entries(entries: List[str], images_dir: Path, class_to_idx: Dict[str, int]) -> List[Tuple[Path, int]]:
    """将 entry（形如 class_name/file_name）解析为 (图像路径, 标签索引)。"""
    pairs: List[Tuple[Path, int]] = []
    for e in entries:
        cls_name = e.split('/')[0]
        label = class_to_idx[cls_name]
        img_path = images_dir / (e + ".jpg")
        pairs.append((img_path, label))
    return pairs


def _stratified_split(train_entries: List[str], val_ratio: float, seed: int = 42) -> Tuple[List[str], List[str]]:
    """按类别分层划分训练/验证列表，保证各类别比例一致。"""
    by_class: Dict[str, List[str]] = {}
    for e in train_entries:
        cls_name = e.split('/')[0]
        by_class.setdefault(cls_name, []).append(e)

    random.seed(seed)
    val_entries: List[str] = []
    new_train_entries: List[str] = []
    for cls, items in by_class.items():
        random.shuffle(items)
        k = max(1, int(len(items) * val_ratio))
        val_entries.extend(items[:k])
        new_train_entries.extend(items[k:])
    return new_train_entries, val_entries


class Food101Dataset(Dataset):
    """将样本列表封装为 PyTorch Dataset，按需应用变换。"""

    def __init__(self, samples: List[Tuple[Path, int]], transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, label


def get_transforms(image_size: int = 224):
    """
    定义训练与评估阶段的图像变换流水线。

    注意：若使用 EfficientNet-B3，建议将 image_size 设为 300。
    如需配合 ImageNet 预训练权重的均值方差标准化，可在末尾添加：
    transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])。
    """
    train_tf = transforms.Compose([
        transforms.Resize((image_size, image_size)),  # 统一尺寸（你可改为 300×300）
        transforms.RandomHorizontalFlip(p=0.5),      # 随机水平翻转
        transforms.RandomRotation(degrees=15),       # 随机旋转（±15°）
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.02),  # 颜色抖动
        transforms.ToTensor(),                        # 归一化到 [0,1]
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((image_size, image_size)),  # 评估阶段不做随机增强
        transforms.ToTensor(),
    ])
    return train_tf, eval_tf


def build_datasets(base_dir: Path, val_ratio: float = 0.1, seed: int = 42):
    """构建 train/val/test 三个 Dataset，并返回类别映射与验证列表。"""
    food_dir = base_dir / "food-101"
    images_dir = food_dir / "images"
    meta_dir = food_dir / "meta"

    classes_txt = meta_dir / "classes.txt"
    train_txt = meta_dir / "train.txt"
    test_txt = meta_dir / "test.txt"

    class_to_idx = _build_class_map(classes_txt)
    train_entries = _read_lines(train_txt)
    test_entries = _read_lines(test_txt)

    new_train_entries, val_entries = _stratified_split(train_entries, val_ratio=val_ratio, seed=seed)

    train_samples = _parse_entries(new_train_entries, images_dir, class_to_idx)
    val_samples = _parse_entries(val_entries, images_dir, class_to_idx)
    test_samples = _parse_entries(test_entries, images_dir, class_to_idx)

    # 若你使用 EfficientNet-B3，建议改为 get_transforms(image_size=300)
    train_tf, eval_tf = get_transforms(image_size=224)
    train_ds = Food101Dataset(train_samples, transform=train_tf)
    val_ds = Food101Dataset(val_samples, transform=eval_tf)
    test_ds = Food101Dataset(test_samples, transform=eval_tf)

    return train_ds, val_ds, test_ds, class_to_idx, val_entries


def get_dataloaders(base_dir: Path, batch_size: int = 32, num_workers: int = 4, val_ratio: float = 0.1, seed: int = 42):
    """构建并返回三个 DataLoader，默认开启 pin_memory 以提升 GPU 训练吞吐。"""
    train_ds, val_ds, test_ds, class_to_idx, val_entries = build_datasets(base_dir, val_ratio=val_ratio, seed=seed)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    return train_loader, val_loader, test_loader, class_to_idx, val_entries


def save_val_list(base_dir: Path, val_entries: List[str]):
    """将生成的验证集列表保存到 meta/val.txt。"""
    meta_dir = base_dir / "food-101" / "meta"
    out_path = meta_dir / "val.txt"
    out_path.write_text("\n".join(val_entries), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    # 示例运行：生成验证集列表并打印基本信息
    base = Path(__file__).resolve().parent
    tl, vl, tsl, class_to_idx, val_entries = get_dataloaders(base_dir=base, batch_size=32, num_workers=4, val_ratio=0.1, seed=42)
    val_path = save_val_list(base, val_entries)
    print(f"Classes: {len(class_to_idx)}")
    print(f"Train batches: {len(tl)}, Val batches: {len(vl)}, Test batches: {len(tsl)}")
    print(f"Validation list saved: {val_path}")

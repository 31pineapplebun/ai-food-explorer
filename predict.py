"""
Food-101 模型预测脚本
=====================

功能描述：
1. 加载训练好的 EfficientNet-B3 模型 (best_efficientnet_b3_food101.pth)。
2. 读取类别列表 (food-101/meta/classes.txt)。
3. 对指定图片进行预处理和预测，输出 Top-5 预测结果。

使用方法：
    python predict.py <图片路径>

示例：
    python predict.py food-101/images/apple_pie/1005649.jpg
"""

import argparse
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from pathlib import Path

# 配置参数
MODEL_PATH = "best_efficientnet_b3_food101.pth"
CLASSES_PATH = "food-101/meta/classes.txt"
NUM_CLASSES = 101
IMAGE_SIZE = 224  # 必须与训练时保持一致 (默认 224)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_classes(path):
    """读取类别名称列表"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"找不到类别文件: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def initialize_model(num_classes):
    """
    初始化 EfficientNet-B3 模型结构
    注意：必须与训练时的结构完全一致
    """
    # 既然我们要加载完整的训练权重，初始化时不需要下载 ImageNet 权重 (weights=None)
    # 但为了保证结构一致，使用 models.efficientnet_b3() 即可
    model = models.efficientnet_b3(weights=None)
    
    # 替换最后一层全连接层
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    
    return model

def load_trained_model(model_path, num_classes):
    """加载模型结构并载入权重"""
    model = initialize_model(num_classes)
    
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到模型文件: {path}")
    
    print(f"正在加载模型: {path} ...")
    # map_location 确保在 CPU 上也能加载 GPU 训练的模型
    state_dict = torch.load(path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model = model.to(DEVICE)
    model.eval()  # 设为评估模式
    return model

def preprocess_image(image_path):
    """读取并预处理图像"""
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"找不到图片: {img_path}")
        
    image = Image.open(img_path).convert("RGB")
    
    # 预处理必须与训练时的验证集处理一致
    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        # 如果训练时使用了均值方差归一化，这里也需要加上
        # transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) 
    ])
    
    return transform(image).unsqueeze(0)  # 增加 batch 维度: [1, 3, 224, 224]

def predict(model, image_tensor, classes, topk=5):
    """执行预测并返回 Top-K 结果"""
    image_tensor = image_tensor.to(DEVICE)
    
    with torch.no_grad():
        outputs = model(image_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)
        
    probs, indices = torch.topk(probabilities, topk)
    
    results = []
    for p, idx in zip(probs[0], indices[0]):
        results.append((classes[idx], p.item()))
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Food-101 图片预测脚本")
    parser.add_argument("image_path", type=str, help="待预测的图片路径")
    args = parser.parse_args()
    
    # 1. 加载类别
    try:
        classes = load_classes(CLASSES_PATH)
        print(f"成功加载 {len(classes)} 个类别。")
    except Exception as e:
        print(f"错误: {e}")
        return

    # 2. 加载模型
    try:
        model = load_trained_model(MODEL_PATH, NUM_CLASSES)
    except Exception as e:
        print(f"错误: {e}")
        return

    # 3. 预测
    try:
        print(f"正在处理图片: {args.image_path}")
        img_tensor = preprocess_image(args.image_path)
        
        # 直接进行预测，移除可能导致兼容性问题的计时代码
        results = predict(model, img_tensor, classes)

        print("\n=== 预测结果 (Top-5) ===")
        for cls_name, prob in results:
            print(f"{cls_name:<20}: {prob*100:.2f}%")
            
    except Exception as e:
        print(f"预测出错: {e}")

if __name__ == "__main__":
    main()

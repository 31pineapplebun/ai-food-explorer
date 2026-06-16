"""
EfficientNet-B3 训练脚本 (Food-101)
===================================

功能描述：
1. 加载经过预处理的 Food-101 数据集（通过 preprocess_food101.py）。
2. 初始化 EfficientNet-B3 模型，加载 ImageNet 预训练权重。
3. 修改模型最后一层全连接层以适配 101 个食物类别。
4. 使用 AdamW 优化器和交叉熵损失函数进行训练。
5. 实现早停（Early Stopping）机制，监测验证集准确率。
6. 保存验证集上表现最好的模型权重。

依赖库：
- torch, torchvision
- preprocess_food101 (自定义模块)
"""

import time
import copy
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torchvision import models
from tqdm import tqdm  # 导入 tqdm 用于显示进度条

# 导入自定义的数据加载函数
try:
    from preprocess_food101 import get_dataloaders
except ImportError:
    raise ImportError("请确保 preprocess_food101.py 在当前目录下，以便加载数据。")

# ============================
# 配置参数
# ============================
BATCH_SIZE = 32          # 批大小
LEARNING_RATE = 1e-4     # 初始学习率
NUM_EPOCHS = 5          # 最大训练轮数
PATIENCE = 5             # 早停耐心值（多少个 epoch 无提升则停止）
NUM_CLASSES = 101        # Food-101 类别数
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def initialize_model(num_classes, feature_extract=False):
    """
    初始化 EfficientNet-B3 模型
    Args:
        num_classes (int): 输出类别数 (101)
        feature_extract (bool): 是否冻结特征提取层（这里默认False，进行全量微调）
    Returns:
        model: 初始化好的 PyTorch 模型
    """
    print("正在加载预训练的 EfficientNet-B3 模型...")
    # 加载 ImageNet 预训练权重
    # weights="DEFAULT" 相当于 weights="IMAGENET1K_V1"
    model = models.efficientnet_b3(weights="DEFAULT")

    # 如果需要冻结特征层（仅训练分类头），可取消下面注释
    if feature_extract:
        for param in model.parameters():
            param.requires_grad = False

    # 获取分类器的输入特征维度
    # EfficientNet 的 classifier 结构通常是: Sequential(Dropout, Linear)
    # 我们取出 Linear 层的 in_features
    # model.classifier[1] 是 Linear 层
    num_ftrs = model.classifier[1].in_features

    # 替换最后一层全连接层
    # 保持原有的 Dropout (model.classifier[0])，替换 Linear
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    
    return model

class EarlyStopping:
    """
    早停工具类：监测验证集指标，如果长时间无提升则停止训练
    """
    def __init__(self, patience=5, verbose=False, delta=0):
        """
        Args:
            patience (int): 容忍多少个 epoch 没有提升
            verbose (bool): 是否打印日志
            delta (float): 认定为提升的最小变化量
        """
        self.patience = patience
        self.verbose = verbose
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        self.val_acc_max = -float('inf')
        self.delta = delta

    def __call__(self, val_acc, model, path):
        score = val_acc

        if self.best_score is None:
            self.best_score = score
            self.save_checkpoint(val_acc, model, path)
        elif score < self.best_score + self.delta:
            self.counter += 1
            if self.verbose:
                print(f'EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.save_checkpoint(val_acc, model, path)
            self.counter = 0

    def save_checkpoint(self, val_acc, model, path):
        '''当验证集准确率提升时保存模型'''
        if self.verbose:
            print(f'验证集准确率提升 ({self.val_acc_max:.4f} --> {val_acc:.4f}).  正在保存模型...')
        torch.save(model.state_dict(), path)
        self.val_acc_max = val_acc

def train_model(model, dataloaders, criterion, optimizer, num_epochs=25, patience=5):
    """
    模型训练主循环
    """
    since = time.time()

    # 用于保存最佳模型路径
    save_path = Path("best_efficientnet_b3_food101.pth")
    
    # 初始化早停对象
    early_stopping = EarlyStopping(patience=patience, verbose=True)

    # 记录训练过程中的 Loss 和 Acc
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}

    for epoch in range(num_epochs):
        print(f'Epoch {epoch + 1}/{num_epochs}')
        print('-' * 10)

        # 每个 epoch 包含训练和验证两个阶段
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()  # 训练模式
            else:
                model.eval()   # 评估模式

            running_loss = 0.0
            running_corrects = 0

            # 使用 tqdm 创建进度条
            # dataloaders[phase] 可能会比较耗时，特别是第一次加载
            pbar = tqdm(dataloaders[phase], desc=f'{phase} Phase', leave=True)

            for inputs, labels in pbar:
                inputs = inputs.to(DEVICE)
                labels = labels.to(DEVICE)

                # 梯度清零
                optimizer.zero_grad()

                # 前向传播
                # 只有在训练阶段才追踪梯度
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    # 反向传播 + 优化 (仅在训练阶段)
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                # 统计 loss 和 acc
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                
                # 更新进度条显示的当前 Loss
                pbar.set_postfix({'loss': f'{loss.item():.4f}'})
            
            epoch_loss = running_loss / len(dataloaders[phase].dataset)
            epoch_acc = running_corrects.double() / len(dataloaders[phase].dataset)

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            # 记录历史数据
            if phase == 'train':
                history['train_loss'].append(epoch_loss)
                history['train_acc'].append(epoch_acc.item())
            else:
                history['val_loss'].append(epoch_loss)
                history['val_acc'].append(epoch_acc.item())
                
                # 早停检查 (基于验证集准确率)
                early_stopping(epoch_acc, model, save_path)
                
        if early_stopping.early_stop:
            print("早停触发 (Early Stopping)")
            break

        print()

    time_elapsed = time.time() - since
    print(f'训练完成，耗时: {time_elapsed // 60:.0f}分 {time_elapsed % 60:.0f}秒')
    print(f'最佳验证集准确率: {early_stopping.val_acc_max:.4f}')

    # 加载最佳模型权重
    model.load_state_dict(torch.load(save_path))
    return model, history

def main():
    # 强制检查 GPU 并打印信息
    if torch.cuda.is_available():
        print(f"✅ 检测到 GPU: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA Version: {torch.version.cuda}")
    else:
        print("⚠️ 未检测到 GPU，正在使用 CPU。训练将非常缓慢！")
        print("   请检查 PyTorch 是否安装了 CUDA 版本 (torch.version.cuda)")
        
    print(f"当前使用设备: {DEVICE}")

    # 1. 准备数据
    base_dir = Path(__file__).resolve().parent
    print("正在准备数据加载器...")
    # 调用 preprocess_food101.py 中的 get_dataloaders
    train_loader, val_loader, test_loader, class_to_idx, val_entries = get_dataloaders(
        base_dir=base_dir,
        batch_size=BATCH_SIZE,
        num_workers=4,   # Windows下如果报错可改为0
        val_ratio=0.1
    )
    
    dataloaders = {
        'train': train_loader,
        'val': val_loader,
        'test': test_loader
    }
    
    print(f"训练集大小: {len(train_loader.dataset)}")
    print(f"验证集大小: {len(val_loader.dataset)}")
    print(f"类别数量: {len(class_to_idx)}")

    # 2. 初始化模型
    model = initialize_model(NUM_CLASSES)
    model = model.to(DEVICE)

    # 3. 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    
    # 使用 AdamW 优化器，学习率 1e-4
    # weight_decay 是 AdamW 的默认特性 (通常 1e-2)，这里使用默认值即可，或者显式指定
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    # 4. 开始训练
    print("开始训练...")
    model, history = train_model(
        model, 
        dataloaders, 
        criterion, 
        optimizer, 
        num_epochs=NUM_EPOCHS, 
        patience=PATIENCE
    )

    # 5. (可选) 保存最终模型
    # torch.save(model.state_dict(), 'final_efficientnet_b3.pth')

if __name__ == '__main__':
    main()




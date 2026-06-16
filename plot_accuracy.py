
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math

def plot_accuracy_final():
    # 1. 读取数据
    try:
        df = pd.read_csv("evaluation_results.csv", index_col=0)
    except FileNotFoundError:
        print("错误：找不到 evaluation_results.csv 文件。")
        return

    df_classes = df.iloc[:-3]
    metric = 'f1-score'
    
    classes = df_classes.index.tolist()
    scores = df_classes[metric].tolist()
    num_classes = len(classes)
    
    # 颜色定义
    COLOR_HIGH = '#2ecc71'
    COLOR_LOW = '#e74c3c'
    COLOR_NORMAL = '#3498db'
    COLOR_LINE = '#bdc3c7'
    
    num_parts = 4
    items_per_chart = math.ceil(num_classes / num_parts)
    
    # 字体设置 (尝试通用字体，避免字体缺失导致显示问题)
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    for i in range(num_parts):
        start = i * items_per_chart
        end = min((i + 1) * items_per_chart, num_classes)
        
        if start >= num_classes:
            break
            
        sub_classes = classes[start:end]
        sub_scores = scores[start:end]
        
        # 创建画布 - 纯净的 Matplotlib
        fig, ax = plt.subplots(figsize=(16, 12), dpi=300)
        
        x_pos = np.arange(len(sub_classes))
        
        # 绘制网格
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        # 绘制连线
        ax.plot(x_pos, sub_scores, color=COLOR_LINE, linewidth=2, zorder=1, alpha=0.6)
        
        # 绘制散点
        colors = []
        sizes = []
        for score in sub_scores:
            if score >= 0.9:
                colors.append(COLOR_HIGH)
                sizes.append(150)
            elif score <= 0.4:
                colors.append(COLOR_LOW)
                sizes.append(150)
            else:
                colors.append(COLOR_NORMAL)
                sizes.append(80)
        
        ax.scatter(x_pos, sub_scores, c=colors, s=sizes, zorder=2, edgecolors='white', linewidth=1.5)
        
        # --- 绝杀方案：手动绘制 X 轴标签 ---
        # 1. 隐藏原本的 X 轴刻度标签
        ax.set_xticks(x_pos)
        ax.set_xticklabels([''] * len(sub_classes)) # 设为空字符串
        
        # 2. 使用 text() 手动绘制
        # transform=ax.get_xaxis_transform() 让 y=0 代表 x轴位置，y<0 代表轴下方
        for idx, label_text in zip(x_pos, sub_classes):
            ax.text(idx, -0.05, label_text, 
                    rotation=90, 
                    ha='center', 
                    va='top', 
                    fontsize=12,
                    transform=ax.get_xaxis_transform()) # 相对于X轴坐标系
        # --- 绝杀方案结束 ---

        # 数值标签
        for j, (x_idx, y) in enumerate(zip(x_pos, sub_scores)):
            label = f'{y:.2f}'
            if y >= 0.9:
                ax.annotate(label, (x_idx, y), xytext=(0, 15), textcoords='offset points',
                           ha='center', va='bottom', fontsize=11, fontweight='bold', color=COLOR_HIGH,
                           bbox=dict(boxstyle='round,pad=0.2', fc='white', ec=COLOR_HIGH, alpha=0.9))
            elif y <= 0.4:
                ax.annotate(label, (x_idx, y), xytext=(0, -15), textcoords='offset points',
                           ha='center', va='top', fontsize=11, fontweight='bold', color=COLOR_LOW,
                           bbox=dict(boxstyle='round,pad=0.2', fc='white', ec=COLOR_LOW, alpha=0.9))
            else:
                ax.annotate(label, (x_idx, y), xytext=(0, 10), textcoords='offset points',
                           ha='center', va='bottom', fontsize=10, color='#7f8c8d')

        ax.set_ylim(-0.1, 1.2)
        ax.set_ylabel('F1 Score', fontsize=14, fontweight='bold', labelpad=15, color='#2c3e50')
        ax.set_title(f'Food-101 Model Performance Analysis (Part {i+1})', fontsize=20, fontweight='bold', pad=30, color='#2c3e50')
        
        # 移除顶部和右侧边框
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # 图例
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Excellent (>=0.9)', markerfacecolor=COLOR_HIGH, markersize=12),
            Line2D([0], [0], marker='o', color='w', label='Poor (<=0.4)', markerfacecolor=COLOR_LOW, markersize=12),
            Line2D([0], [0], marker='o', color='w', label='Normal', markerfacecolor=COLOR_NORMAL, markersize=10)
        ]
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, fancybox=True, shadow=True)

        # 调整布局
        # bottom=0.22 给竖排标签留出22%的高度空间，这应该足够了且不会太宽
        plt.subplots_adjust(bottom=0.22, top=0.9, left=0.08, right=0.95)
        
        filename = f"accuracy_part_{i+1}.png"
        plt.savefig(filename, dpi=300)
        print(f"✅ 图表已保存: {filename}")
        plt.close()

if __name__ == "__main__":
    plot_accuracy_final()

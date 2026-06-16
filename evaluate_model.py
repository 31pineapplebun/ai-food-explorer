
import torch
import torch.nn as nn
from torchvision import models, transforms, datasets
from torch.utils.data import DataLoader
from pathlib import Path
import json
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# --- Configuration ---
MODEL_PATH = "best_efficientnet_b3_food101.pth"
CLASSES_PATH = "food-101/meta/classes.txt"
TEST_DIR = "test_dataset"
IMAGE_SIZE = 224
BATCH_SIZE = 32
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_classes(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Classes file not found: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def initialize_model(num_classes):
    print("Initializing EfficientNet-B3...")
    model = models.efficientnet_b3(weights=None)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    return model

def evaluate():
    # 1. Load Classes
    classes = load_classes(CLASSES_PATH)
    num_classes = len(classes)
    print(f"Loaded {num_classes} classes.")

    # 2. Setup Data
    test_transforms = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
    ])

    if not Path(TEST_DIR).exists():
        print(f"Error: Test directory '{TEST_DIR}' not found.")
        return

    # Check if directory is empty or has valid structure
    # ImageFolder requires structure: root/class/image.jpg
    try:
        test_dataset = datasets.ImageFolder(root=TEST_DIR, transform=test_transforms)
    except Exception as e:
        print(f"Error loading dataset from {TEST_DIR}: {e}")
        print("Ensure the directory structure is 'test_dataset/class_name/image.jpg'")
        return

    if len(test_dataset) == 0:
        print(f"No images found in {TEST_DIR}.")
        return

    
    print(f"Found {len(test_dataset)} images belonging to {len(test_dataset.classes)} classes.")
    
    dataset_idx_to_model_idx = {}
    for class_name, idx in test_dataset.class_to_idx.items():
        if class_name in classes:
            dataset_idx_to_model_idx[idx] = classes.index(class_name)
        else:
            print(f"Warning: Class '{class_name}' in test set not found in classes.txt")

    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # 3. Load Model
    model = initialize_model(num_classes)
    if not Path(MODEL_PATH).exists():
        print(f"Error: Model file '{MODEL_PATH}' not found.")
        return
    
    state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    print("Model loaded successfully.")

    # 4. Inference
    all_preds = []
    all_labels = []
    
    print("Running inference...")
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(DEVICE)
            # labels from ImageFolder (0..N_subset)
            
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            
            
            true_labels_model_space = [dataset_idx_to_model_idx[l.item()] for l in labels]
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(true_labels_model_space)

    # 5. Metrics
    acc = accuracy_score(all_labels, all_preds)
    print(f"\nTotal Accuracy: {acc:.4f} ({acc*100:.2f}%)")

    # Filter classes that were actually present in the test set
    present_class_indices = sorted(list(set(all_labels)))
    present_class_names = [classes[i] for i in present_class_indices]
    
    print("\nClassification Report:")
    print(classification_report(all_labels, all_preds, labels=present_class_indices, target_names=present_class_names, zero_division=0))

    # Save to file
    report = classification_report(all_labels, all_preds, labels=present_class_indices, target_names=present_class_names, output_dict=True, zero_division=0)
    df = pd.DataFrame(report).transpose()
    df.to_csv("evaluation_results.csv")
    print("Detailed results saved to 'evaluation_results.csv'")

if __name__ == "__main__":
    evaluate()

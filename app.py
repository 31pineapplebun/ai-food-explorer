import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import io
import json
import requests
import random
from hashlib import md5
from typing import List, Dict, Optional
from pydantic import BaseModel

# --- Configuration ---
MODEL_PATH = "best_efficientnet_b3_food101.pth"
CLASSES_PATH = "food-101/meta/classes.txt"
RECIPES_PATH = "recipes/final_recipes.json"
IMAGE_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- App Initialization ---
app = FastAPI(title="Food-101 Recipe Recommender")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Variables ---
model = None
classes = []
recipes_db = {}

# --- Model & Data Loading ---
def load_classes(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Classes file not found: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def load_recipes(path):
    path = Path(path)
    if not path.exists():
        print(f"Warning: Recipes file not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def initialize_model(num_classes):
    # Initialize EfficientNet-B3 with the same structure as training
    # For inference, we don't need pretrained ImageNet weights, we load our own later
    # Using weights=None to avoid downloading weights
    # Note: torchvision >= 0.13 uses 'weights', older versions use 'pretrained'
    try:
        model = models.efficientnet_b3(weights=None)
    except TypeError:
        # Fallback for older torchvision versions
        model = models.efficientnet_b3(pretrained=False)
        
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    return model

@app.on_event("startup")
async def startup_event():
    global model, classes, recipes_db
    
    print("Initializing application...")
    
    # 1. 加载类别列表
    try:
        classes = load_classes(CLASSES_PATH)
        print(f"✅ Loaded {len(classes)} food classes.")
    except Exception as e:
        print(f"❌ Error loading classes: {e}")
        
    # 2. 加载预先匹配好的食谱数据库
    try:
        recipes_db = load_recipes(RECIPES_PATH)
        print(f"✅ Loaded recipes for {len(recipes_db)} categories.")
    except Exception as e:
        print(f"❌ Error loading recipes: {e}")

    # 3. 加载并初始化 EfficientNet-B3 模型
    try:
        model = initialize_model(len(classes))
        
        if not Path(MODEL_PATH).exists():
            print(f"❌ Model file not found: {MODEL_PATH}")
        else:
            state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
            model.load_state_dict(state_dict)
            model.to(DEVICE)
            model.eval()
            print(f"✅ Model loaded successfully on {DEVICE}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")

# --- Inference Helper ---
def transform_image(image_bytes):
    """
    Transform the input image bytes to a tensor.
    Matches the validation transform from training (Resize + ToTensor).
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        # Note: Normalize is skipped to match training configuration
    ])
    return transform(image).unsqueeze(0).to(DEVICE)

# --- API Endpoints ---

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Endpoint to predict food category and return recipes.
    """
    if model is None:
        raise HTTPException(status_code=500, detail="Model is not loaded.")
    if not classes:
        raise HTTPException(status_code=500, detail="Classes are not loaded.")

    try:
        # Read and transform image
        image_bytes = await file.read()
        image_tensor = transform_image(image_bytes)
        
        # 模型推理
        with torch.no_grad():
            outputs = model(image_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)        
        # Get Top-5 Predictions
        topk_probs, topk_indices = torch.topk(probabilities, 5)
        # 获取 Top-1 类别
        top_idx = topk_indices[0][0].item()
        top_class = classes[top_idx]
        top_conf = topk_probs[0][0].item()        
        # 查库与去重
        matched_recipes = recipes_db.get(top_class, [])
        unique_recipes = {}
        for recipe in matched_recipes:
            title = recipe.get('title', '').strip()
            if title and title not in unique_recipes:
                unique_recipes[title] = recipe       
        # 返回 Top-5 结果
        matched_recipes = list(unique_recipes.values())[:5]       
        # Construct Response
        results = {
            "prediction": top_class,
            "confidence": float(top_conf),
            "top_5_predictions": [
                {
                    "class": classes[idx.item()],
                    "probability": float(prob.item())
                }
                for prob, idx in zip(topk_probs[0], topk_indices[0])
            ],
            "recipes": matched_recipes
        }
        
        return results
        
    except Exception as e:
        print(f"Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Translation Service ---

# Baidu Translation API Credentials
# 百度翻译 API 凭证：从环境变量读取，不在仓库中保存明文密钥
# Windows (PowerShell): $env:BAIDU_APP_ID="你的AppID"; $env:BAIDU_APP_KEY="你的Key"
# Linux / macOS:        export BAIDU_APP_ID=你的AppID BAIDU_APP_KEY=你的Key
BAIDU_APP_ID = os.environ.get('BAIDU_APP_ID', '')
BAIDU_APP_KEY = os.environ.get('BAIDU_APP_KEY', '')
BAIDU_ENDPOINT = 'http://api.fanyi.baidu.com'
BAIDU_PATH = '/api/trans/vip/translate'
BAIDU_URL = BAIDU_ENDPOINT + BAIDU_PATH

# --- Translation Cache ---
# 简单的内存缓存，存储 { "query_text": {API Response JSON} }
# 优化目标：(d) 模型部署优化 - 提升响应速度，减少 API 调用
TRANSLATION_CACHE = {}

class TranslateRequest(BaseModel):
    text: str
    from_lang: str = 'en'
    to_lang: str = 'zh'

def make_md5(s, encoding='utf-8'):
    return md5(s.encode(encoding)).hexdigest()

@app.post("/translate")
async def translate_text(request: TranslateRequest):
    """
    Translate text using Baidu Translation API with Caching.
    """
    query = request.text
    if not query:
        raise HTTPException(status_code=400, detail="Text is required")

    # [Optimization] Check Cache first
    # 如果同样的文本之前翻译过，直接返回缓存结果，无需请求百度
    cache_key = f"{query}_{request.from_lang}_{request.to_lang}"
    if cache_key in TRANSLATION_CACHE:
        print(f"⚡ Cache Hit for: {query[:10]}...")
        return TRANSLATION_CACHE[cache_key]

    salt = random.randint(32768, 65536)
    sign = make_md5(BAIDU_APP_ID + query + str(salt) + BAIDU_APP_KEY)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'appid': BAIDU_APP_ID, 
        'q': query, 
        'from': request.from_lang, 
        'to': request.to_lang, 
        'salt': salt, 
        'sign': sign
    }
    try:
        r = requests.post(BAIDU_URL, params=payload, headers=headers)
        result = r.json()
        
        if 'error_code' in result:
            # Return 200 with error info or 400, but handle it cleanly
            # We raise HTTPException, but we need to ensure it's not caught by the general Exception handler below if we want the 400 to propagate
            raise HTTPException(status_code=400, detail=f"Baidu API Error: {result.get('error_msg')}")
            
        # [Optimization] Save to Cache
        # 仅当翻译成功时才缓存
        if 'trans_result' in result:
             TRANSLATION_CACHE[cache_key] = result
             
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Translation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static directory to serve frontend files
# Create 'static' folder if it doesn't exist
static_path = Path("static")
static_path.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

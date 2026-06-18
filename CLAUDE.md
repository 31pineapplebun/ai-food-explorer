# CLAUDE.md — Food Explorer（前端 React 重构）

## 项目简介
拍照识别食物并推荐食谱的 Web 应用。用户上传/拍摄一张食物图片，前端调用后端识别接口，展示识别结果（食物名 + 置信度）与 Top-5 食谱推荐。

## 重构背景（重要）
- 这是一次**前端重写**：原版是纯原生 HTML/CSS/JS 单文件，现在用 **React + Vite** 重做成一个 SPA。
- **后端不动**：沿用已有的 FastAPI 服务（EfficientNet 食物识别 + Sentence-BERT 食谱匹配）。前端只通过 REST API 调用它，不要去碰模型/后端逻辑。
- 这是一个**学习 + 面试项目**。请优先写「我能读懂、能讲清楚」的代码：清晰、地道的 React，不要过度抽象、不要过早优化。做了不直观的决定时，留一行注释说明**为什么**这么做。

## 技术栈
- React 18（函数组件 + Hooks）
- Vite（构建 / 开发服务器）
- 原生 `fetch`（**不引入** axios / react-query —— 让异步逻辑显式可见，便于讲解）
- CSS Modules（样式按组件隔离）
- JavaScript（JSX）。暂不用 TypeScript，先把 React 本身吃透。

## 常用命令
```bash
npm install        # 安装依赖
npm run dev        # 本地开发（默认 http://localhost:5173）
npm run build      # 生产构建
npm run preview    # 预览构建产物
npm run lint       # ESLint 检查
```

## 目录结构
```
src/
  api/
    foodApi.js          # 所有后端请求收在这里
  components/
    UploadArea.jsx       # 选图 / 拖拽上传
    ImagePreview.jsx     # 选中图片预览
    ResultCard.jsx       # 识别结果（食物名 + 置信度）
    RecipeList.jsx       # 食谱列表
    RecipeCard.jsx       # 单个食谱卡片
    Loading.jsx
    ErrorMessage.jsx
  App.jsx               # 页面装配 + 顶层状态
  main.jsx              # 入口
```

## 后端接口（按你的真实后端调整）
- `POST /api/recognize`，`multipart/form-data`，图片字段名 `file`
- 返回示例：
  ```json
  {
    "food": "宫保鸡丁",
    "confidence": 0.82,
    "recipes": [
      { "id": 1, "name": "...", "ingredients": ["..."], "steps": ["..."] }
    ]
  }
  ```

## 约定与规则
- **只用函数组件 + Hooks**，不用 class 组件。
- 组件**小而单一职责**；展示型组件不直接发请求——请求封装在 `api/foodApi.js`，由 `App` 调用后通过 props 把数据下发。
- 文件输入用**非受控写法**（`onChange` 读 `event.target.files[0]`，用 `ref` 做重置）；选图后用 `URL.createObjectURL` 生成预览，换图 / 卸载时 `URL.revokeObjectURL` 释放。
- 异步请求必须**显式处理四种状态**：loading / error / 成功 / 空。
- 列表渲染（食谱卡片）**必须用稳定 key**：用后端返回的 `id`，**不要用数组下标**。
- 状态默认 `useState`；若"选图 → 识别 → 结果"的状态变复杂，再换 `useReducer`，并注释说明原因。
- **不要随意加依赖**（UI 库、状态库等）；确有必要先说清理由再加。

## 这个项目应清晰体现的 React 概念（面试要能指着代码讲）
组件拆分与 props 传递、`useState` 状态管理、**非受控的文件输入**（以及为什么文件输入天然非受控）、条件渲染（四态切换）、列表渲染与 key、把请求/副作用从 UI 组件中分离、`useEffect` 做副作用清理（释放预览 URL）。

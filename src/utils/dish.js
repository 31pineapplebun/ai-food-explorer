import { DISH } from '../data/dishes.js'

// 类别标签 → { zh 中文名, en 英文名, intro 一句话简介 }
export function dishName(label) {
  const en = (label || '').replace(/_/g, ' ')
  const d = DISH[label]
  if (d) return { zh: d[0], en, intro: d[1] }
  // 兜底：没收录的标签就把英文美化一下（首字母大写）
  const zh = en.replace(/\b\w/g, (c) => c.toUpperCase())
  return { zh, en, intro: '看起来很好吃的一道菜～' }
}

// 置信度 → { stars 0~5, label 文案 }
// 故意不用冷冰冰的百分比，而是星级 + 一句白话，更像「点评」的口吻。
export function confInfo(c) {
  if (c >= 0.85) return { stars: 5, label: '基本就是它了' }
  if (c >= 0.65) return { stars: 4.5, label: '很可能是这道' }
  if (c >= 0.45) return { stars: 4, label: '应该是这道' }
  if (c >= 0.3) return { stars: 3.5, label: '大概是这道' }
  if (c >= 0.18) return { stars: 3, label: '有点拿不准，看看下面' }
  return { stars: 2.5, label: '不太确定，参考其他猜测' }
}

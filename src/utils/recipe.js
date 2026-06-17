// 食材 / 步骤可能是数组，也可能是 JSON 字符串（后端两种都可能给）。
// 统一成数组；解析失败就原样返回（说明它本来就是一句普通字符串）。
export function parseList(value) {
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : value
    } catch {
      return value
    }
  }
  return value
}

// 匹配度 score → 文案标签（不直接暴露原始分数）
export function matchLabel(score) {
  if (score == null) return '推荐'
  if (score >= 0.7) return '很搭'
  if (score >= 0.5) return '挺搭'
  return '可以试'
}

// 食材名 → 淘宝搜索链接
export function taoUrl(q) {
  return 'https://s.taobao.com/search?q=' + encodeURIComponent(q)
}

// 翻译时的节流小工具
export function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

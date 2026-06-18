// 所有后端请求都收在这里：UI 组件不直接写 fetch，便于统一维护、也便于讲解。

// 带超时的 fetch：弱网或后端卡住时主动放弃，避免请求一直挂起、页面一直转圈。
// 这是个很常用的小工具，放在本文件里给两个请求复用（不算过度抽象）。
async function fetchWithTimeout(url, options = {}, ms = 20000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), ms)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

// 识别：POST /predict，multipart/form-data。
// 字段名必须是 "file"（对应后端 `file: UploadFile = File(...)`），否则会 422。
export async function predictFood(file) {
  const formData = new FormData()
  formData.append('file', file)
  let res
  try {
    res = await fetchWithTimeout('/predict', { method: 'POST', body: formData })
  } catch (e) {
    // 超时被 abort 时给一句更友好的话；App 的 catch 会把它落到错误态并可重试
    if (e.name === 'AbortError') throw new Error('网络好像不太顺，等会儿再试试～')
    throw e
  }
  if (!res.ok) throw new Error('服务器开小差了 (' + res.status + ')')
  return res.json()
}

// 翻译：POST /translate，JSON { text }。
// 返回拼好的中文字符串（多行用 \n 连接），让调用方不必关心百度的返回结构。
export async function translateText(text) {
  if (!text || !String(text).trim()) return text
  const res = await fetchWithTimeout('/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: String(text) }),
  })
  // 这条 message 只进 console；用户看到的是 RecipeCard 自己 catch 后展示的友好提示
  if (!res.ok) throw new Error('translate ' + res.status)
  const data = await res.json()
  if (data.trans_result && data.trans_result.length) {
    return data.trans_result.map((x) => x.dst).join('\n')
  }
  return null
}

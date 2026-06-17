// 所有后端请求都收在这里：UI 组件不直接写 fetch，便于统一维护、也便于讲解。

// 识别：POST /predict，multipart/form-data。
// 字段名必须是 "file"（对应后端 `file: UploadFile = File(...)`），否则会 422。
export async function predictFood(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/predict', { method: 'POST', body: formData })
  if (!res.ok) throw new Error('服务器开小差了 (' + res.status + ')')
  return res.json()
}

// 翻译：POST /translate，JSON { text }。
// 返回拼好的中文字符串（多行用 \n 连接），让调用方不必关心百度的返回结构。
export async function translateText(text) {
  if (!text || !String(text).trim()) return text
  const res = await fetch('/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: String(text) }),
  })
  if (!res.ok) throw new Error('translate ' + res.status)
  const data = await res.json()
  if (data.trans_result && data.trans_result.length) {
    return data.trans_result.map((x) => x.dst).join('\n')
  }
  return null
}

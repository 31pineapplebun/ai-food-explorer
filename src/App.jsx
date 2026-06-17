import { useEffect, useRef, useState } from 'react'
import UploadArea from './components/UploadArea.jsx'
import ImagePreview from './components/ImagePreview.jsx'
import Loading from './components/Loading.jsx'
import ErrorMessage from './components/ErrorMessage.jsx'
import ResultCard from './components/ResultCard.jsx'
import RecipeList from './components/RecipeList.jsx'
import { predictFood } from './api/foodApi.js'
import { dishName, confInfo } from './utils/dish.js'
import styles from './App.module.css'

// 顶层组件：持有所有状态，是唯一发起识别请求的地方，再把数据通过 props 下发给展示组件。
export default function App() {
  // 用单个 status 枚举表达「四态」，保证 loading/error/success 互斥（比 4 个布尔值清晰）
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [status, setStatus] = useState('idle') // 'idle' | 'loading' | 'success' | 'error'
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('') // 轻量瞬时提示（非图片/未选图），与四态 status 解耦，避免污染识别结果

  const fileInputRef = useRef(null) // 用来重置非受控的文件输入
  const feedbackRef = useRef(null) // 识别后滚动到这片反馈区

  function handleFile(f) {
    if (!f || !f.type.startsWith('image/')) {
      // 拖拽 / 选文件可能绕过 accept，这里兜底。
      // 用独立的轻量 notice，而不是切到 error 状态——否则会把已有的识别结果替换掉、还会触发滚动（与原版不一致）。
      setNotice('这看起来不是图片，换一张图片试试～')
      return
    }
    setNotice('')
    setFile(f) // 预览 URL 交给下面的 useEffect 处理
    setResult(null)
    setStatus('idle') // 选了新图，回到「待识别」
  }

  function handleReset() {
    setFile(null)
    setResult(null)
    setStatus('idle')
    setError('')
    setNotice('')
    // 必须清空，否则再次选「同一个文件」不会触发 onChange
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function recognize() {
    if (!file) {
      // 按钮在没有文件时本就禁用，这里只是防御；用 notice 提示，不污染识别状态
      setNotice('先选一张图片吧～')
      return
    }
    setStatus('loading')
    setError('')
    try {
      const data = await predictFood(file)
      setResult(data)
      setStatus('success')
    } catch (e) {
      setError(e.message || '没认出来，再试一次吧～')
      setStatus('error')
    }
  }

  // 选中文件后生成预览 URL；换图 / 卸载时释放，避免内存泄漏。
  // 预览图和结果页的主图共用这一个 URL（结果卡不自己再 createObjectURL），
  // 所以 cleanup 撤销的永远是「已经不显示」的旧 URL，不会把正在显示的图撤掉。
  useEffect(() => {
    if (!file) {
      setPreviewUrl('')
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  // 粘贴上传：监听整个文档的 paste（是全局行为，所以放在 App 而不是某个子组件里），
  // 卸载时移除监听。handleFile 只调用 setState，不依赖外部变量，故空依赖即可。
  useEffect(() => {
    function onPaste(e) {
      const items = (e.clipboardData || {}).items || []
      for (const it of items) {
        if (it.type.indexOf('image') !== -1) {
          const f = it.getAsFile()
          if (f) {
            handleFile(f)
            break
          }
        }
      }
    }
    document.addEventListener('paste', onPaste)
    return () => document.removeEventListener('paste', onPaste)
  }, [])

  // 加载 / 成功 / 失败时，平滑滚动到反馈区（尊重「减少动态效果」的系统偏好）
  useEffect(() => {
    if (status === 'idle' || !feedbackRef.current) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    feedbackRef.current.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
  }, [status])

  const buttonLabel =
    status === 'loading' ? '正在认… 🍳' : result ? '再认一张 👀' : '认一认 👀'

  // 把识别结果整理成结果卡需要的「视图模型」，让 ResultCard 保持纯展示
  let hero = null
  if (result) {
    const info = dishName(result.prediction)
    const ci = confInfo(result.confidence || 0)
    hero = {
      photoUrl: previewUrl,
      zh: info.zh,
      en: info.en,
      intro: info.intro,
      stars: ci.stars,
      confLabel: ci.label,
      // top-5 去掉第一个（就是主结果），其余作为「也可能是」
      alts: (result.top_5_predictions || []).slice(1, 5).map((a) => ({
        key: a.class,
        zh: dishName(a.class).zh,
      })),
    }
  }

  return (
    <div className={styles.wrap}>
      <header className={styles.brand}>
        <div className={styles.logo}>
          <span className={styles.em}>🍜</span>
          <span>嗨，这道菜</span>
        </div>
        <div className={styles.tag}>
          拍一拍 / 拖张图进来，<b>一拍就知道叫什么</b>，还顺手送你做法 🥢
        </div>
      </header>

      <section className={styles.panel}>
        <UploadArea inputRef={fileInputRef} onFile={handleFile} />
        {previewUrl && <ImagePreview src={previewUrl} onReset={handleReset} />}
        <div className={styles.actions}>
          <button
            className={styles.btn}
            onClick={recognize}
            disabled={!file || status === 'loading'}
          >
            {buttonLabel}
          </button>
        </div>
        {notice && <div className={styles.notice}>{notice}</div>}
      </section>

      {/* 四态切换：loading / error / success（empty 由 RecipeList 内部处理） */}
      <div ref={feedbackRef}>
        {status === 'loading' && <Loading />}
        {status === 'error' && <ErrorMessage message={error} onRetry={recognize} />}
        {status === 'success' && hero && (
          <main className={styles.result}>
            <ResultCard {...hero} />
            <RecipeList recipes={result.recipes || []} />
          </main>
        )}
      </div>

      <div className={styles.foot}>
        嗨，这道菜 · 拍图认菜，做法随手收
        <br />
        认得不一定全对，当个有趣的参考就好 🙂
      </div>
    </div>
  )
}

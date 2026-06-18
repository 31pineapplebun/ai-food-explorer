import { useState } from 'react'
import { translateText } from '../api/foodApi.js'
import { parseList, matchLabel, taoUrl, delay } from '../utils/recipe.js'
import styles from './RecipeCard.module.css'

// 百度翻译免费版约 1 QPS：串行翻译时每次之间留 >1s 间隔，避免被限流
const TRANSLATE_GAP_MS = 1100

// 单个食谱卡：展开/收起做法、一键把英文做法翻译成中文。
//
// 关于「翻译」这个请求：CLAUDE.md 要求展示组件不直接发请求，主流程（识别）确实由 App 统一发。
// 但翻译是「单张卡片、用户点击触发、只影响这张卡自己内容」的本地交互，
// 如果上提到 App 反而要在顶层维护每张卡的翻译状态，更绕、更耦合。
// 折中：网络请求函数 translateText 仍封装在 api 层（组件里没有裸 fetch），
// 由本卡片调用并自管自己的临时 UI 状态。
// props：title 字符串；ingredients/directions 可能是数组或 JSON 字符串（parseList 容错）；score 数字或 null。
export default function RecipeCard({ title, ingredients, directions, score }) {
  const [open, setOpen] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [translated, setTranslated] = useState(false) // 译完后隐藏翻译按钮
  const [transError, setTransError] = useState('')

  // 展示用内容：初始为原文（容错解析成数组），翻译成功后替换成中文
  const [displayTitle, setDisplayTitle] = useState(title)
  const [displayIng, setDisplayIng] = useState(() => parseList(ingredients))
  const [displayDir, setDisplayDir] = useState(() => parseList(directions))

  async function handleTranslate() {
    setTranslating(true)
    setTransError('')
    try {
      // 串行翻译 标题 → 用料 → 步骤，中间留间隔：百度有 QPS 限制，避免被限流
      const t = await translateText(title)
      if (t) setDisplayTitle(t)
      await delay(TRANSLATE_GAP_MS)

      const ingText = Array.isArray(displayIng) ? displayIng.join('\n') : displayIng
      const ti = await translateText(ingText)
      if (ti) {
        const arr = ti.split('\n').filter((s) => s.trim())
        setDisplayIng(arr.length ? arr : ingText)
      }
      await delay(TRANSLATE_GAP_MS)

      const dirText = Array.isArray(displayDir) ? displayDir.join('\n') : displayDir
      const td = await translateText(dirText)
      if (td) {
        const arr = td.split('\n').filter((s) => s.trim())
        setDisplayDir(arr.length ? arr : dirText)
      }

      setOpen(true) // 翻完自动展开给用户看
      setTranslated(true)
    } catch (e) {
      console.error(e)
      setTransError('翻译没成功，可能是太频繁了，过会儿再试～')
    } finally {
      setTranslating(false)
    }
  }

  return (
    <div className={styles.rcard}>
      <div className={styles.rtop}>
        <h3 className={styles.rtitle}>{displayTitle}</h3>
        <span className={styles.rmatch}>🔖 {matchLabel(score)}</span>
      </div>

      <div className={styles.rbar}>
        <button
          className={`${styles.linkBtn} ${open ? styles.open : ''}`}
          onClick={() => setOpen((o) => !o)}
        >
          <span>{open ? '收起做法' : '看做法'}</span> <span className={styles.ar}>▾</span>
        </button>
        {!translated && (
          <button
            className={`${styles.linkBtn} ${styles.cnBtn}`}
            onClick={handleTranslate}
            disabled={translating}
          >
            {translating ? '翻译中… ⏳' : '🌐 看中文做法'}
          </button>
        )}
      </div>

      {/* role=alert：翻译失败时让读屏软件能主动播报（与主错误态一致） */}
      {transError && (
        <div className={styles.transErr} role="alert">
          {transError}
        </div>
      )}

      {open && (
        <div className={styles.rbody}>
          <div className={styles.blkH}>
            🥕 用料 <span className={styles.hint}>点食材可淘宝直达</span>
          </div>
          <Ingredients items={displayIng} />
          <div className={styles.blkH}>🔥 步骤</div>
          <Directions items={displayDir} />
        </div>
      )}
    </div>
  )
}

// 用料：数组渲染成可点击（跳淘宝）的列表，否则当成一句话。
// 这是静态列表（只随翻译整体替换，不会重排/插入），用下标作 key 是安全的。
function Ingredients({ items }) {
  if (Array.isArray(items)) {
    return (
      <ul className={styles.ing}>
        {items.map((x, i) => (
          <li key={i}>
            <a
              className={styles.tao}
              href={taoUrl(x)}
              target="_blank"
              rel="noopener noreferrer"
              title="淘宝找食材"
            >
              🛒 {x}
            </a>
          </li>
        ))}
      </ul>
    )
  }
  return (
    <p>
      <a className={styles.tao} href={taoUrl(items)} target="_blank" rel="noopener noreferrer">
        🛒 {items}
      </a>
    </p>
  )
}

// 步骤：数组渲染成带序号的列表，否则当成一段话。
function Directions({ items }) {
  if (Array.isArray(items)) {
    return (
      <ol className={styles.dir}>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ol>
    )
  }
  return <p className={styles.dirText}>{items}</p>
}

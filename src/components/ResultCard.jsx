import styles from './ResultCard.module.css'

// 识别结果的主卡（hero）。纯展示组件：要显示的内容（中文名、星级、简介、备选）
// 都由 App 提前算好后通过 props 传进来，这里不含任何业务逻辑。
export default function ResultCard({ photoUrl, zh, en, intro, stars, confLabel, alts }) {
  return (
    <>
      <div className={styles.secH}>应该是这道菜~ 🍽️</div>
      <div className={styles.hero}>
        {/* 主图就是用户刚上传的那张，菜名紧接着用文字给出 → 图片是装饰性的，alt 留空避免读屏重复念菜名 */}
        {photoUrl && <img className={styles.pic} src={photoUrl} alt="" />}
        <div className={styles.body}>
          <div className={styles.nm}>{zh}</div>
          <div className={styles.en}>{en}</div>
          <div className={styles.conf}>
            {/* 星级：底层灰星 + 上层金星，用宽度百分比裁切出「几颗星」 */}
            <span className={styles.stars}>
              <span className={styles.fill} style={{ width: (stars / 5) * 100 + '%' }} />
            </span>
            <span className={styles.lab}>{confLabel}</span>
          </div>
          <div className={styles.intro}>{intro}</div>
          {alts.length > 0 && (
            <div className={styles.alts}>
              <div className={styles.altsH}>也可能是 👇</div>
              <div>
                {alts.map((a) => (
                  // 后端无 id；class 是唯一的食物标签 → 稳定 key（不用数组下标）
                  <span key={a.key} className={styles.chip}>
                    {a.zh}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

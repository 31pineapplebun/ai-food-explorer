import styles from './Loading.module.css'

// 骨架屏：识别时显示。比起转圈 loading，它更接近内容最终的样子，体感更快、更稳。
export default function Loading() {
  return (
    <div className={styles.skel} aria-busy="true" aria-label="正在识别…">
      <div className={styles.sk}>
        <div className={`${styles.pic} ${styles.shimmer}`} />
        <div className={`${styles.ln} ${styles.w1} ${styles.shimmer}`} />
        <div className={`${styles.ln} ${styles.w2} ${styles.shimmer}`} />
        <div className={`${styles.ln} ${styles.w3} ${styles.shimmer}`} />
        <div className={styles.spacer} />
      </div>
      <div className={styles.sk}>
        <div className={`${styles.ln} ${styles.w2} ${styles.shimmer}`} style={{ marginTop: 18 }} />
        <div className={`${styles.ln} ${styles.w3} ${styles.shimmer}`} />
        <div className={styles.spacer} />
      </div>
    </div>
  )
}

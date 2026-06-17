import styles from './ErrorMessage.module.css'

// 错误态：取代原来的 alert()，做成页面内的提示卡片 + 重试。
// role="alert" 让读屏软件在出错时能主动播报（弥补去掉 alert 后的可访问性）。
export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className={styles.box} role="alert">
      <div className={styles.face}>😅</div>
      <div className={styles.msg}>{message || '出了点小状况，再试一次吧～'}</div>
      {onRetry && (
        <button className={styles.retry} onClick={onRetry}>
          再试一次
        </button>
      )}
    </div>
  )
}

import styles from './ImagePreview.module.css'

// 选中图片的预览 + 右上角「换一张」按钮。展示型组件，src 由父组件传入。
export default function ImagePreview({ src, onReset }) {
  return (
    <div className={styles.preview}>
      <img className={styles.img} src={src} alt="你上传的图" />
      <button className={styles.re} onClick={onReset} aria-label="换一张" title="换一张">
        ✕
      </button>
    </div>
  )
}

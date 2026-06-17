import { useState } from 'react'
import styles from './UploadArea.module.css'

// 选图区：点击 / 拖拽 / 键盘都能触发文件选择。文件输入是「非受控」的（见下方注释）。
// 这是展示型组件：它只负责把选中的文件交给 onFile，自己不发任何请求。
export default function UploadArea({ inputRef, onFile }) {
  const [dragging, setDragging] = useState(false) // 仅用于拖拽时的高亮，纯本地 UI 状态

  function openPicker() {
    inputRef.current?.click()
  }

  return (
    <div
      className={`${styles.drop} ${dragging ? styles.drag : ''}`}
      role="button"
      tabIndex={0}
      onClick={openPicker}
      onKeyDown={(e) => {
        // 让键盘用户也能用 Enter / 空格打开文件选择框
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          openPicker()
        }
      }}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={(e) => {
        e.preventDefault()
        setDragging(false)
      }}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        const f = e.dataTransfer.files && e.dataTransfer.files[0]
        if (f) onFile(f)
      }}
    >
      <div className={styles.cam}>📷</div>
      <div className={styles.t1}>
        点这里、拖张图、或 <span className={styles.kbd}>Ctrl+V</span> 贴一张
      </div>
      <div className={styles.t2}>支持 JPG / PNG，越清晰越认得准</div>

      {/*
        文件输入天生是「非受控」的：它的值是用户挑选的只读 FileList，
        出于安全考虑 React（以及浏览器）不允许用 value 去设定要选哪个文件（只能清空）。
        所以这里不绑 value，而是在 onChange 里读 e.target.files[0]，
        并由父组件用 ref 在换图 / 重置时清空它（input.value = ''）。
      */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          const f = e.target.files[0]
          if (f) onFile(f)
        }}
      />
    </div>
  )
}

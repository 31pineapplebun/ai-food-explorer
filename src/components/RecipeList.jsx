import RecipeCard from './RecipeCard.jsx'
import styles from './RecipeList.module.css'

// 食谱区：标题 + 列表。识别成功但「没收录做法」的空态在这里处理。
export default function RecipeList({ recipes }) {
  return (
    <>
      <div className={styles.secH}>顺手收几个做法 📖</div>
      {recipes.length === 0 ? (
        <div className={styles.empty}>这道菜暂时没收录做法，下次补上～ 🙏</div>
      ) : (
        recipes.map((r) => (
          // 后端没有 id，但已按 title 去重 → 同一次结果里 title 唯一稳定，用作 key。
          // 满足「用稳定 key、不用数组下标」的本意（CLAUDE.md 也说明按真实后端调整）。
          <RecipeCard
            key={r.title}
            title={r.title}
            ingredients={r.ingredients}
            directions={r.directions}
            score={r.score}
          />
        ))
      )}
    </>
  )
}

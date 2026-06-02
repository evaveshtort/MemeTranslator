import React from 'react'
import styles from './SkeletonCard.module.css'

const HEIGHTS = [240, 320, 200]

export default function SkeletonCard({ index = 0 }) {
  return <div className={styles.card} style={{ height: HEIGHTS[index % HEIGHTS.length] }} />
}

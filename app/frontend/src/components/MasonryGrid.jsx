import React from 'react'
import styles from './MasonryGrid.module.css'

export default function MasonryGrid({ children, compact }) {
  return <div className={`${styles.grid} ${compact ? styles.compact : ''}`}>{children}</div>
}

import dayjs from 'dayjs'

/**
 * 格式化時間 ISO 字串為 YYYY-MM-DD HH:mm:ss
 */
export function formatTime(isoString) {
  if (!isoString) return ''
  return dayjs(isoString).format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 將維修建議字串中的逗號轉換為 HTML 換行標籤 <br>
 */
export function formatSuggestion(text) {
  if (!text) return ''
  return text.split(',').join('<br>')
}

/**
 * 從 PLC 紀錄中提取包含 'NG' 的欄位名稱 (m01 ~ m12)
 */
export function extractNgItems(record) {
  if (!record) return []
  const checks = ['m01', 'm02', 'm03', 'm04', 'm05', 'm06', 'm07', 'm08', 'm09', 'm10', 'm11', 'm12']
  return checks.filter(key => record[key]?.includes('NG'))
}

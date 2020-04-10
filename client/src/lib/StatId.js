import moment from 'moment-timezone'

export function statIdToInfo (statid) {
  const file = statid.match(/\/([^/]+\.json)$/)

  let term = null
  let label = null
  if (file) {
    const m = file[1].match(/([0-9]+)_([0-9]+)_([0-9]+)_(([a-zA-Z0-9]+)_)?([0-9a-f-]+)\.json/)
    if (m) {
      const start = moment.utc(m[2], 'YYYYMMDDHHmmss')
      const end = moment.utc(m[3], 'YYYYMMDDHHmmss')
      term = `${start.format('YYYY/MM/DD HH:mm:ss')}〜${end.format('YYYY/MM/DD HH:mm:ss')}`
      label = m[5]
    }
  }

  return {
    name: statid,
    term,
    label
  }
}

/* eslint-disable camelcase */
export interface IOrgUsageDetail {
  type: string
  size: number
  tid: string
}

export interface IOrgUsage {
  athena_scan_size: number
  collect_size: number
  details: IOrgUsageDetail[]
  month: number
}
/* eslint-enable */

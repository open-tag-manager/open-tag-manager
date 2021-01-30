/* eslint-disable camelcase */
export interface IStat {
  label: string
  stime: number
  etime: number
  status: string
  timestamp: string
  // eslint-disable-next-line camelcase
  job_id: string
  // eslint-disable-next-line camelcase
  raw_file_key: string
  // eslint-disable-next-line camelcase
  file_key: string
  // eslint-disable-next-line camelcase
  file_url: string
}

export interface IStatDataMeta {
  etime: number
  stime: number
  tid: string
  type: string
  version: number
}

export interface IStatDataTable {
  datetime: string
  url: string
  p_url?: string

  count: number

  event_count: number
  user_count: number
  session_count: number

  t_click_count: number
  w_click_count: number

  s_count: number
  max_scroll_y: number
  sum_scroll_y: number
  avg_scroll_y?: number

  plt_count: number
  max_plt: number
  sum_plt: number
  avg_plt?: number
}

export interface IStatDataLink {
  count: number
  url: string
  p_url?: string
  title?: string
}

export interface IStatData {
  meta: IStatDataMeta
  table: IStatDataTable[]
  url_links: IStatDataLink[]
  urls: string[]
}
/* eslint-enable */

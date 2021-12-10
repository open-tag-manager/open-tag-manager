/* eslint-disable camelcase */
export interface IStat {
  label: string
  stime: number
  etime: number
  status: string
  timestamp: string
  job_id: string
  raw_file_key: string
  file_key: string
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

export interface IStatPageviewTimeSeriesTable {
  date: string
  pageview_count: number
  pageview_count_3days: number
  pageview_count_7days: number
  pageview_count_14days: number
  pageview_count_30days: number

  session_count: number
  session_count_3days: number
  session_count_7days: number
  session_count_14days: number
  session_count_30days: number

  user_count: number
  user_count_3days: number
  user_count_7days: number
  user_count_14days: number
  user_count_30days: number
}

export interface IStatDataLink {
  count: number
  url: string
  p_url?: string
  title?: string
}

export interface IStatUrlLinkData {
  meta: IStatDataMeta
  url_links: IStatDataLink[]
  urls: string[]
}

export interface IStatEventTable {
  label: string | null
  state: string | null
  title: string | null
  url: string | null
  count: number
}

export interface IStatUrlTableData {
  meta: IStatDataMeta
  table: IStatDataTable[]
}

export interface IStatEventTableData {
  meta: IStatDataMeta
  table: IStatEventTable[]
}

export interface IStatPageviewTimeSeriesData {
  meta: IStatDataMeta
  table: IStatPageviewTimeSeriesTable[]
}
/* eslint-enable */

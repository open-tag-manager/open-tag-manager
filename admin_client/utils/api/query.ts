/* eslint-disable camelcase */

export interface IQueryExecution {
  execution_id: string
}

export type TQueryResultState =
  | 'QUEUED'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLED'

export interface IQueryResult<T> {
  state: TQueryResultState
  items: T[]
  next: string | null
}

export interface IQueryResultFile {
  state: TQueryResultState
  file: string | null
}

/* eslint-enable camelcase */

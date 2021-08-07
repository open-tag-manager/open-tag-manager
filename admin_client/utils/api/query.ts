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

/* eslint-enable camelcase */

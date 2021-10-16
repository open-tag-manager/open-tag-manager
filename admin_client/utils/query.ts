import API from '@aws-amplify/api'
import Cookie from 'js-cookie'
import {
  IQueryExecution,
  IQueryResult,
  IQueryResultFile,
} from '~/utils/api/query'
import {IStatEventTableData, IStatUrlTableData} from '~/utils/api/stat'

const delay = (seconds: number): Promise<void> => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve()
    }, seconds)
  })
}

const waitTableQuery = async (
  path: string,
  id: string,
  org: string,
  container: string,
  stime: number,
  etime: number
): Promise<IQueryResultFile> => {
  const result: IQueryResultFile = await API.post(
    'OTMClientAPI',
    `/orgs/${org}/containers/${container}/stats/query_result_${path}`,
    {
      body: {
        execution_id: id,
        stime,
        etime,
      },
    }
  )
  if (result.state === 'SUCCEEDED') {
    return result
  }
  if (result.state === 'FAILED' || result.state === 'CANCELLED') {
    throw new Error('Failed to load')
  }
  await delay(1000)
  return waitTableQuery(path, id, org, container, stime, etime)
}

const tableQuery = async <T>(
  path: string,
  org: string,
  container: string,
  stime: number,
  etime: number
): Promise<T> => {
  const execute: IQueryExecution = await API.post(
    'OTMClientAPI',
    `/orgs/${org}/containers/${container}/stats/start_query_${path}`,
    {
      body: {
        stime,
        etime,
      },
    }
  )
  const result = await waitTableQuery(
    path,
    execute.execution_id,
    org,
    container,
    stime,
    etime
  )

  if (result.file) {
    const response: Response = await fetch(result.file, { method: 'GET' })
    const data: T = await response.json()
    return data
  }

  throw new Error('File not found')
}

export const urlTableQuery = async (
  org: string,
  container: string,
  stime: number,
  etime: number
) => {
  return await tableQuery<IStatUrlTableData>(
    'url_table',
    org,
    container,
    stime,
    etime
  )
}

export const eventTableQuery = async (
  org: string,
  container: string,
  stime: number,
  etime: number
) => {
  return await tableQuery<IStatEventTableData>(
    'event_table',
    org,
    container,
    stime,
    etime
  )
}

/* eslint-disable camelcase */
export type TGoalMatchPattern = 'eq' | 'prefix' | 'regex'

export interface IGoal {
  id?: string
  name: string
  result_url?: string | null
  target: string
  target_match: TGoalMatchPattern
  path?: string | null
  path_match: TGoalMatchPattern
  label?: string | null
  label_match?: TGoalMatchPattern
}
/* eslint-enable  */

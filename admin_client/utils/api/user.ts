/* eslint-disable camelcase */
export interface IUserOrgRole {
  org: string
  roles: string[]
}

export interface IUser {
  created_at: number
  updated_at: number
  username: string
  email?: string
  orgs: IUserOrgRole[]
}

export interface IOrgUser {
  created_at: number
  updated_at: number
  roles: string[]
  username: string
  email: string
}
/* eslint-enable */

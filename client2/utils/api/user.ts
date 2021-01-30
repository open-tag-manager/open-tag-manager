export interface IUserOrgRole {
  org: string
  roles: string[]
}

export interface IUser {
  // eslint-disable-next-line camelcase
  created_at: number
  // eslint-disable-next-line camelcase
  updated_at: number
  username: string
  orgs: IUserOrgRole[]
}

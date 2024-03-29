import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators'
import Auth, { CognitoUser } from '@aws-amplify/auth'
import API from '@aws-amplify/api'
import { IUser } from '~/utils/api/user'

@Module({
  name: 'session',
  stateFactory: true,
  namespaced: true,
})
export default class Session extends VuexModule {
  user: CognitoUser | null = null
  otmUser: IUser | null = null

  @Mutation
  setUser(user: CognitoUser) {
    this.user = user
  }

  @Mutation
  setOtmUser(user: IUser) {
    this.otmUser = user
  }

  @Action
  async init() {
    try {
      const user: CognitoUser = await Auth.currentAuthenticatedUser()
      this.context.commit('setUser', user)
      const otmUser: IUser = await API.get('OTMClientAPI', '/user', {})
      this.context.commit('setOtmUser', otmUser)
      if (window.OTM) {
        window.OTM.setUid(user.getUsername())
      }
    } catch (_e) {}
  }

  @Action
  async signOut() {
    try {
      await Auth.signOut()
    } catch (_e) {}

    this.context.commit('setUser', null)
    this.context.commit('setOtmUser', null)

    if (window.OTM) {
      window.OTM.unsetUid()
    }
  }

  get hasAdminRole() {
    return (orgName: string): boolean => {
      if (this.hasRootAdminRole) {
        return true
      }

      if (this.otmUser) {
        if (
          this.otmUser.orgs.find((o) => {
            return o.org === orgName && o.roles.includes('admin')
          })
        ) {
          return true
        }
      }

      return false
    }
  }

  get hasRootAdminRole(): boolean {
    if (this.otmUser) {
      if (
        this.otmUser.orgs.find(
          (o) => o.org === 'root' && o.roles.includes('admin')
        )
      ) {
        return true
      }
    }

    return false
  }
}

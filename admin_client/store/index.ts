import { ActionTree, Store } from 'vuex'
import { initialiseStores, session } from '~/utils/store-accessor'

const initializer = (store: Store<any>) => initialiseStores(store)
export const plugins = [initializer]

export const actions: ActionTree<any, any> = {
  async nuxtClientInit() {
    await session.init()
  },
}

export * from '~/utils/store-accessor'

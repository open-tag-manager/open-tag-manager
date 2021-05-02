import { Store } from 'vuex'
import { getModule } from 'vuex-module-decorators'
import Session from '~/store/session'

// eslint-disable-next-line import/no-mutable-exports
let session: Session

function initialiseStores(store: Store<any>): void {
  session = getModule(Session, store)
}

export { initialiseStores, session }

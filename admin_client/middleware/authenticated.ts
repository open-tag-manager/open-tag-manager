import { Middleware } from '@nuxt/types'
import { session } from '~/store'

const authenticated: Middleware = ({ redirect }) => {
  if (!session.user) {
    return redirect('/signin')
  }
}

export default authenticated

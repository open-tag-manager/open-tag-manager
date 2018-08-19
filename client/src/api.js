import axios from 'axios'
import _ from 'lodash'

export default (store, overwrite = {}) => {
  const params = {
    baseURL: process.env.API_BASE_URL,
    timeout: 60000,
    headers: {}
  }

  if (store.state.user.token) {
    params.headers.Authorization = store.state.user.token
  }

  return axios.create(_.extend(params, overwrite))
}

const state = {
  swaggerDoc: null,
  editableSwaggerDoc: null,
  swaggerDocRevision: 0,
  container: null,
  org: null,
  containers: null
}

const mutations = {
  SET_SWAGGER_DOC (state, {swaggerDoc, r = 0}) {
    state.swaggerDoc = swaggerDoc
    state.editableSwaggerDoc = swaggerDoc
    state.swaggerDocRevision = r
  },
  EDIT_SWAGGER_DOC (state, {swaggerDoc}) {
    state.editableSwaggerDoc = swaggerDoc
  },
  SET_CONTAINER (state, {org, container}) {
    state.org = org
    state.container = container
  },
  SET_CONTAINERS (state, {containers}) {
    state.containers = containers
  }
}

const actions = {
  async fetchContainer ({commit}, {org, container}) {
    const data = await this.app.$Amplify.API.get('OTMClientAPI', `/orgs/${org}/containers/${container}`)
    commit('SET_CONTAINER', {container: data, org: org})
    commit('SET_SWAGGER_DOC', {swaggerDoc: JSON.stringify(data.swagger_doc)})
  },
  async saveContainer ({commit, state}, params) {
    const data = await this.app.$Amplify.API.put('OTMClientAPI', `/orgs/${state.org}/containers/${state.container.tid}`, {body: params})
    commit('SET_CONTAINER', {container: data, org: state.org})
  },
  editSwaggerDoc ({commit}, {swaggerDoc}) {
    commit('EDIT_SWAGGER_DOC', {swaggerDoc})
  },
  async saveSwaggerDoc ({commit, dispatch, state}) {
    await dispatch('saveContainer', {swagger_doc: JSON.parse(state.editableSwaggerDoc)})
    commit('SET_SWAGGER_DOC', {swaggerDoc: state.editableSwaggerDoc, r: state.swaggerDocRevision + 1})
  },
  setCurrentContainer ({commit}, {org, container}) {
    commit('SET_CONTAINER', {org, container})
    if (container) {
      commit('SET_SWAGGER_DOC', {swaggerDoc: JSON.stringify(container.swagger_doc)})
    } else {
      commit('SET_SWAGGER_DOC', {swaggerDoc: null})
    }
  },
  async fetchContainers (ctx, {org}) {
    const data = await this.app.$Amplify.API.get('OTMClientAPI', `/orgs/${org}/containers`)
    ctx.commit('SET_CONTAINERS', {containers: data.items})
  }
}

const getters = {
  getSwaggetDocPaths (state) {
    if (!state.swaggerDoc) {
      return {}
    }

    const doc = JSON.parse(state.swaggerDoc)
    return doc.paths || {}
  }
}

export default {
  state,
  mutations,
  actions,
  getters,
  namespaced: true
}

const state = {
  swaggerDoc: null,
  editableSwaggerDoc: null,
  swaggerDocRevision: 0,
  container: null,
  containers: []
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
  SET_CONTAINER (state, {container}) {
    state.container = container
  },
  SET_CONTAINERS (state, {containers}) {
    state.containers = containers
  }
}

const actions = {
  async fetchSwaggerDoc (ctx, {org, container}) {
    const data = await this.app.$Amplify.API.get('OTMClientAPI', `/orgs/${org}/containers/${container}/swagger_doc`)
    ctx.commit('SET_SWAGGER_DOC', {swaggerDoc: JSON.stringify(data)})
  },
  editSwaggerDoc (ctx, {swaggerDoc}) {
    ctx.commit('EDIT_SWAGGER_DOC', {swaggerDoc})
  },
  async saveSwaggerDoc (ctx, {org, container}) {
    await this.app.$Amplify.API.put('OTMClientAPI', `/orgs/${org}/containers/${container}/swagger_doc`, {body: JSON.parse(ctx.state.editableSwaggerDoc)})
    ctx.commit('SET_SWAGGER_DOC', {swaggerDoc: ctx.state.editableSwaggerDoc, r: ctx.state.swaggerDocRevision + 1})
  },
  setCurrentContainer (ctx, {container}) {
    ctx.commit('SET_CONTAINER', {container})
  },
  async fetchContainers (ctx, {org}) {
    const data = await this.app.$Amplify.API.get('OTMClientAPI', `/orgs/${org}/containers`)
    ctx.commit('SET_CONTAINERS', {containers: data})
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

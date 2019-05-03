const state = {
  swaggerDoc: null,
  editableSwaggerDoc: null,
  swaggerDocRevision: 0
}

const mutations = {
  SET_SWAGGER_DOC (state, {swaggerDoc, r = 0}) {
    state.swaggerDoc = swaggerDoc
    state.editableSwaggerDoc = swaggerDoc
    state.swaggerDocRevision = r
  },
  EDIT_SWAGGER_DOC (state, {swaggerDoc}) {
    state.editableSwaggerDoc = swaggerDoc
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
  }
}

export default {
  state,
  mutations,
  actions,
  namespaced: true
}

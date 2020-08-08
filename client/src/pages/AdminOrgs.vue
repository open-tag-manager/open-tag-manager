<template>
  <div class="container py-2">
    <h2>Orgs</h2>

    <table class="table">
      <thead>
      <tr>
        <th>Name</th>
        <th>Operation</th>
      </tr>
      </thead>

      <tbody>
      <tr v-for="org in orgs" :key="org.name">
        <td>{{org.name}}</td>
        <td>
          <b-button variant="primary" :to="{'name': 'Org-Settings', params: {org: org.name}}">Setting</b-button>
        </td>
      </tr>
      </tbody>
    </table>

    <button class="btn btn-primary" @click="loadNext" v-if="next">Load next</button>

    <h2>Create org</h2>
    <b-form @submit.prevent="createOrg">
      <b-form-group label="Org name">
        <b-form-input v-model="org"  placeholder="Org name" required pattern="^[0-9A-Za-z_-]+$"></b-form-input>
      </b-form-group>
      <b-button variant="primary" type="submit">Create</b-button>
    </b-form>
  </div>
</template>

<script>
  export default {
    data () {
      return {
        orgs: [],
        next: null,
        org: ''
      }
    },
    async created () {
      await this.load()
    },
    methods: {
      async load () {
        const data = await this.$Amplify.API.get('OTMClientAPI', '/orgs')
        this.orgs = data.items
        this.next = data.next
      },
      async createOrg () {
        await this.$Amplify.API.post('OTMClientAPI', '/orgs', {
          body: {
            name: this.org
          }
        })
        this.org = ''
        await this.load()
      },
      async loadNext () {
        const data = await this.$Amplify.API.get('OTMClientAPI', '/orgs', {queryStringParameters: {next: this.next}})
        this.orgs = [...this.orgs, ...data.items]
        this.next = data.next
      }
    }
  }
</script>

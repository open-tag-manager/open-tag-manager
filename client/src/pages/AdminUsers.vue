<template>
  <div class="container py-2">
    <h2>Users</h2>

    <table class="table">
      <thead>
      <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Orgs</th>
        <th>Operation</th>
      </tr>
      </thead>

      <tbody>
      <tr v-for="user in users" :key="user.username">
        <td>{{user.username}}</td>
        <td>{{user.email}}</td>
        <td>
          <ul>
            <li v-for="org in user.orgs" :key="org.org">{{org.org}}</li>
          </ul>
        </td>
        <td>
          <button class="btn btn-danger" :disabled="user.username === 'root'" @click="removeUser(user)">Remove</button>
        </td>
      </tr>
      </tbody>
    </table>

    <button class="btn btn-primary" @click="loadNext" v-if="next">Load next</button>

    <h2>Invite user</h2>
    <b-form @submit.prevent="createUser">
      <b-form-group label="Username">
        <b-form-input v-model="username"  placeholder="Org name" required pattern="^[0-9A-Za-z_-@]+$"></b-form-input>
      </b-form-group>
      <b-form-group label="Email">
        <b-form-input v-model="email"  placeholder="Email" required type="email"></b-form-input>
      </b-form-group>
      <b-button variant="primary" type="submit">Create</b-button>
    </b-form>
  </div>
</template>

<script>
  export default {
    data () {
      return {
        users: [],
        next: null,
        username: '',
        email: ''
      }
    },
    async created () {
      await this.load()
    },
    methods: {
      async load () {
        const data = await this.$Amplify.API.get('OTMClientAPI', '/users')
        this.users = data.items
        this.next = data.next
      },
      async createUser () {
        await this.$Amplify.API.post('OTMClientAPI', '/users', {
          body: {
            username: this.username,
            email: this.email
          }
        })
        this.username = ''
        this.email = ''
        await this.load()
      },
      async loadNext () {
        const data = await this.$Amplify.API.get('OTMClientAPI', '/users', {queryStringParameters: {next: this.next}})
        this.users = [...this.users, ...data.items]
        this.next = data.next
      },
      async removeUser (user) {
        await this.$Amplify.API.del('OTMClientAPI', `/users/${user.username}`)
        await this.load()
      }
    }
  }
</script>

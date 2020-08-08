<template>
  <div class="container py-2">
    <h2>User List</h2>

    <table class="table">
      <thead>
      <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Roles</th>
        <th>Operation</th>
      </tr>
      </thead>

      <tbody>
      <tr v-for="user in users" :key="user.username">
        <td>{{user.username}}</td>
        <td>{{user.email}}</td>
        <td>{{user.roles | joinRole}}</td>
        <td>
          <button class="btn btn-primary" :disabled="isSelf(user.username) || !hasAdminRole" @click="showEditRoleModal(user)">Edit roles</button>
          <button class="btn btn-danger" :disabled="isSelf(user.username) || !hasAdminRole" @click="removeUser(user)">Remove</button>
        </td>
      </tr>
      </tbody>
    </table>

    <b-modal ref="EditRoleModal" title="Change roles" @ok="editRole">
      <p>Change roles for {{targetUser ? targetUser.username : null}}</p>

      <b-form>
        <b-checkbox-group v-model="roles">
          <b-form-checkbox value="read">Read</b-form-checkbox>
          <b-form-checkbox value="write">Write</b-form-checkbox>
          <b-form-checkbox value="admin">Admin</b-form-checkbox>
        </b-checkbox-group>
      </b-form>
    </b-modal>

    <button class="btn btn-primary" @click="loadNext" v-if="next">Load next</button>

    <div v-if="hasAdminRole">
      <h2>Invite new user</h2>
      <b-form @submit.prevent="invite">
        <b-form-group label="Username">
          <b-form-input v-model="username"  placeholder="Username" required></b-form-input>
          <b-checkbox-group v-model="newUserRoles">
            <b-form-checkbox value="read">Read</b-form-checkbox>
            <b-form-checkbox value="write">Write</b-form-checkbox>
            <b-form-checkbox value="admin">Admin</b-form-checkbox>
          </b-checkbox-group>
        </b-form-group>
        <b-button variant="primary" type="submit">Invite</b-button>
      </b-form>
    </div>
  </div>
</template>

<script>
  export default {
    data () {
      return {
        users: [],
        next: null,
        username: '',
        newUserRoles: ['read', 'write'],
        targetUser: null,
        roles: []
      }
    },
    async created () {
      await this.load()
    },
    methods: {
      async load () {
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/users`)
        this.users = data.items
        this.next = data.next
      },
      async loadNext () {
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/users`, {queryStringParameters: {next: this.next}})
        this.users = [...this.users, ...data.items]
        this.next = data.next
      },
      isSelf (username) {
        return this.$store.state.user.user.username === username
      },
      async removeUser (user) {
        await this.$Amplify.API.del('OTMClientAPI', `/orgs/${this.$route.params.org}/users/${user.username}`)
        await this.load()
      },
      showEditRoleModal (user) {
        this.targetUser = user
        this.roles = [...user.roles]
        this.$refs.EditRoleModal.show()
      },
      async editRole () {
        await this.$Amplify.API.put('OTMClientAPI', `/orgs/${this.$route.params.org}/users/${this.targetUser.username}`, {body: {
          roles: this.roles
        }})
        await this.load()
        this.$refs.EditRoleModal.hide()
      },
      async invite () {
        try {
          await this.$Amplify.API.post('OTMClientAPI', `/orgs/${this.$route.params.org}/users`, {
            body: {
              username: this.username,
              roles: this.newUserRoles
            }
          })
          this.username = ''
          await this.load()
        } catch (e) {
          this.$toasted.show(e.response.data.error, {duration: 3000})
        }
      }
    },
    computed: {
      hasAdminRole () {
        return this.$store.state.user.currentOrg.roles.includes('admin')
      }
    },
    filters: {
      joinRole (roles) {
        return roles.slice().sort().join(', ')
      }
    }
  }
</script>

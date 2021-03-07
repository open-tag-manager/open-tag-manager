<template>
  <v-container>
    <h2 class="mb-2">Users</h2>

    <v-simple-table class="mb-4">
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
          <td>{{ user.username }}</td>
          <td>{{ user.email }}</td>
          <td class="pa-2">
            <ul>
              <li v-for="org in user.orgs" :key="org.org">{{ org.org }}</li>
            </ul>
          </td>
          <td>
            <v-btn
              color="error"
              :disabled="user.username === 'root'"
              @click="removeUser(user)"
              >Remove
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-simple-table>
    <v-progress-linear v-if="isLoading" indeterminate />

    <v-btn v-if="next" class="mb-4" @click="loadNext">Load next</v-btn>

    <h2 class="mb-2">Invite user</h2>
    <invite-user-form @create="load" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { API } from '@aws-amplify/api'
import { IUser } from '~/utils/api/user'
import { PaginationItem } from '~/utils/api/paginationItem'
import InviteUserForm from '~/components/InviteUserForm.vue'
@Component({
  components: { InviteUserForm },
})
export default class AdminUsers extends Vue {
  isLoading: boolean = false

  users: IUser[] = []
  next: string | null = null

  async load() {
    this.isLoading = true
    const data: PaginationItem<IUser> = await API.get(
      'OTMClientAPI',
      '/users',
      {}
    )
    this.users = data.items
    this.next = data.next
    this.isLoading = false
  }

  async loadNext() {
    this.isLoading = true
    const data: PaginationItem<IUser> = await API.get(
      'OTMClientAPI',
      '/users',
      { queryStringParameters: { next: this.next } }
    )
    this.users = [...this.users, ...data.items]
    this.next = data.next
    this.isLoading = false
  }

  async removeUser(user: IUser) {
    await API.del('OTMClientAPI', `/users/${user.username}`, {})
    await this.load()
  }

  async mounted() {
    await this.load()
  }
}
</script>

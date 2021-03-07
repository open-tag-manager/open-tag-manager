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
    <v-form ref="userForm" v-model="newUserValid" @submit.prevent="createUser">
      <v-row>
        <v-col>
          <v-text-field
            v-model="newUserName"
            label="Username"
            aria-required="true"
            :rules="userNameRules"
          />
        </v-col>
        <v-col>
          <v-text-field
            v-model="newUserEmail"
            :rules="emailRules"
            label="Email"
            aria-required="true"
          />
        </v-col>
        <v-col>
          <v-btn type="submit" :disabled="!newUserValid">Create</v-btn>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue, Ref } from 'vue-property-decorator'
import { API } from '@aws-amplify/api'
import { IUser } from '~/utils/api/user'
import { PaginationItem } from '~/utils/api/paginationItem'
import VForm from '~/utils/VForm'

@Component
export default class AdminUsers extends Vue {
  @Ref()
  userForm?: VForm

  isLoading: boolean = false

  newUserValid: boolean = false
  newUserName: string = ''
  newUserEmail: string = ''
  userNameRules = [
    (v: any) => !!v || 'Name is required',
    (v: any) => {
      if (!v) {
        return true
      }

      if (!(v as string).match(/^[0-9A-Za-z_-]+$/)) {
        return 'Correct character is [0-9A-Za-z_-]'
      }

      return true
    },
  ]

  emailRules = [(v: any) => !!v || 'Email is required']

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

  async createUser() {
    await API.post('OTMClientAPI', '/users', {
      body: {
        username: this.newUserName,
        email: this.newUserEmail,
      },
    })
    this.userForm?.reset()
    await this.load()
  }

  async mounted() {
    await this.load()
  }
}
</script>

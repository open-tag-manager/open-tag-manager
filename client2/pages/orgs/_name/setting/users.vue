<template>
  <v-container>
    <h2 class="mb-2">User List</h2>
    <v-simple-table class="mb-4">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Roles</th>
          <th>Operation</th>
        </tr>
      </thead>
      <tbody>
        <org-user-table-row
          v-for="user in users"
          :key="user.username"
          :user="user"
          :org-name="currentOrg"
          :has-admin-role="hasAdminRole"
          @removed="load"
        />
      </tbody>
    </v-simple-table>
    <v-progress-linear v-if="isLoading" indeterminate class="mb-4" />
    <v-btn v-if="next" class="mb-4" @click="loadNext">Load next</v-btn>

    <div v-if="hasAdminRole">
      <h2 class="mb-2">Invite new user</h2>
      <v-form ref="inviteForm" v-model="validUser" @submit.prevent="invite">
        <v-text-field
          v-model="newUserName"
          label="Username"
          aria-required="true"
          :rules="usernameRules"
        />
        <v-row>
          <v-col lg="2">
            <v-checkbox v-model="newUserRoles" label="Read" value="read" />
          </v-col>
          <v-col lg="2">
            <v-checkbox v-model="newUserRoles" label="Write" value="write" />
          </v-col>
          <v-col lg="2">
            <v-checkbox v-model="newUserRoles" label="Admin" value="admin" />
          </v-col>
        </v-row>
        <v-btn type="submit" :disabled="!validUser" @click="invite"
          >Invite</v-btn
        >
      </v-form>
    </div>
    <v-snackbar v-model="snackbar" right top>{{ snackbarMessage }}</v-snackbar>
  </v-container>
</template>

<script lang="ts">
import { Component, Ref } from 'nuxt-property-decorator'
import { API } from '@aws-amplify/api'
import OrgContainer from '~/components/OrgContainer'
import { IOrgUser } from '~/utils/api/user'
import { PaginationItem } from '~/utils/api/paginationItem'
import OrgUserTableRow from '~/components/OrgUserTableRow.vue'
import { session } from '~/store'
import VForm from '~/utils/VForm'

@Component({
  components: { OrgUserTableRow },
})
export default class OrgsSettingUsers extends OrgContainer {
  @Ref()
  inviteForm: VForm

  isLoading: boolean = false

  snackbar: boolean = false
  snackbarMessage: string = ''

  users: IOrgUser[] = []
  next: string = ''

  validUser: boolean = true
  newUserName: string = ''
  newUserRoles: string[] = ['read', 'write']

  usernameRules = [(v: any) => !!v || 'Username is required']

  async load() {
    this.isLoading = true
    const data: PaginationItem<IOrgUser> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/users`
    )
    this.users = data.items
    this.next = data.next

    this.isLoading = false
  }

  async loadNext() {
    this.isLoading = true
    const data: PaginationItem<IOrgUser> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/users`,
      { queryStringParameters: { next: this.next } }
    )
    this.users = [...this.users, ...data.items]
    this.next = data.next
    this.isLoading = false
  }

  get hasAdminRole() {
    return session.hasAdminRole(this.currentOrg)
  }

  async invite() {
    try {
      await API.post('OTMClientAPI', `/orgs/${this.currentOrg}/users`, {
        body: {
          username: this.newUserName,
          roles: this.newUserRoles,
        },
      })
      this.inviteForm?.reset()
      this.newUserRoles = ['read', 'write']
      await this.load()
    } catch (e) {
      this.snackbarMessage = 'Failed to invite user'
      this.snackbar = true
    }
  }

  async mounted() {
    await this.load()
  }
}
</script>

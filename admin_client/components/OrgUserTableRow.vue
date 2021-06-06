<template>
  <tr>
    <td>{{ user.username }}</td>
    <td>{{ user.email }}</td>
    <td class="pa-2">
      <ul>
        <li v-for="role in user.roles" :key="role">{{ role }}</li>
      </ul>
    </td>
    <td>
      <v-btn :disabled="isSelf || !hasAdminRole" @click="openRoleEditModal"
        >Edit roles</v-btn
      >
      <v-btn
        color="error"
        :disabled="isSelf || !hasAdminRole"
        @click="removeUser"
        >Remove</v-btn
      >
      <v-dialog v-model="editModal" max-width="320">
        <template #default>
          <v-card>
            <v-toolbar color="primary" dark> Edit roles </v-toolbar>
            <v-card-text class="pa-4">
              <v-row>
                <v-col>
                  <v-checkbox v-model="editRoles" value="read" label="Read" />
                </v-col>
                <v-col>
                  <v-checkbox v-model="editRoles" value="write" label="Write" />
                </v-col>
                <v-col>
                  <v-checkbox v-model="editRoles" value="admin" label="Admin" />
                </v-col>
              </v-row>
            </v-card-text>
            <v-divider />
            <v-card-actions>
              <v-spacer />
              <v-btn color="primary" @click="saveRole">Save</v-btn>
            </v-card-actions>
          </v-card>
        </template>
      </v-dialog>
    </td>
  </tr>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'nuxt-property-decorator'
import { API } from '@aws-amplify/api'
import { Emit } from 'vue-property-decorator'
import { IOrgUser } from '~/utils/api/user'
import { session } from '~/store'

@Component
export default class OrgUserTableRow extends Vue {
  @Prop({ type: Object, required: true })
  user!: IOrgUser

  @Prop({ type: String, required: true })
  orgName!: string

  @Prop({ type: Boolean, default: false })
  hasAdminRole!: boolean

  editModal: boolean = false

  editRoles: string[] = []

  openRoleEditModal() {
    this.editRoles = [...this.user.roles]
    this.editModal = true
  }

  @Emit('update')
  async saveRole() {
    await API.put(
      'OTMClientAPI',
      `/orgs/${this.orgName}/users/${this.user.username}`,
      {
        body: {
          roles: this.editRoles,
        },
      }
    )
    this.editModal = false
    this.user.roles = this.editRoles
  }

  @Emit('removed')
  async removeUser() {
    await API.del(
      'OTMClientAPI',
      `/orgs/${this.orgName}/users/${this.user.username}`,
      {}
    )
  }

  get isSelf() {
    return session.otmUser!.username === this.user.username
  }
}
</script>

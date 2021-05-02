<template>
  <v-form ref="form" v-model="newUserValid" @submit.prevent="createUser">
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
</template>

<script lang="ts">
import { Component, Vue } from 'nuxt-property-decorator'
import { Emit, Ref } from 'vue-property-decorator'
import { API } from '@aws-amplify/api'
import VForm from '../utils/VForm'

@Component
export default class InviteUserForm extends Vue {
  @Ref()
  form?: VForm

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

  @Emit('create')
  async createUser() {
    await API.post('OTMClientAPI', '/users', {
      body: {
        username: this.newUserName,
        email: this.newUserEmail,
      },
    })
    this.form?.reset()
  }
}
</script>

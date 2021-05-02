<template>
  <v-form ref="form" v-model="valid" @submit.prevent="createOrg">
    <v-row>
      <v-col>
        <v-text-field
          v-model="orgName"
          label="Name"
          aria-required="true"
          :rules="nameRules"
        />
      </v-col>
      <v-col>
        <v-btn :disabled="!valid" type="submit">Save</v-btn>
      </v-col>
    </v-row>
  </v-form>
</template>

<script lang="ts">
import { Component, Vue, Ref } from 'nuxt-property-decorator'
import { API } from '@aws-amplify/api'
import { Emit } from 'vue-property-decorator'
import VForm from '~/utils/VForm'

@Component
export default class NewOrgForm extends Vue {
  @Ref()
  form?: VForm

  valid: boolean = false
  orgName: string = ''
  nameRules = [
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

  @Emit('create')
  async createOrg() {
    await API.post('OTMClientAPI', '/orgs', { body: { name: this.orgName } })
    this.form?.reset()
  }
}
</script>

<template>
  <v-container>
    <v-btn
      text
      class="mb-4"
      :to="{ name: 'orgs-name', params: { name: currentOrg } }"
      ><v-icon>mdi-arrow-left</v-icon>Back</v-btn
    >
    <h1>Create new container for {{ currentOrg }}</h1>
    <v-form ref="form" v-model="valid" lazy-validation @submit.prevent="submit">
      <v-text-field
        v-model="name"
        label="Container name"
        :rules="nameRules"
        class="mb-4"
        required
      ></v-text-field>
      <v-btn type="submit">Create</v-btn>
      {{ name }}
    </v-form>
  </v-container>
</template>

<script lang="ts">
import API from '@aws-amplify/api'
import { Component } from 'vue-property-decorator'
import Org from '~/components/Org'
import VForm from '~/utils/VForm'

@Component
export default class NewContainer extends Org {
  name: string = ''
  nameRules = [(v: string) => !!v || 'Name is required']
  valid: boolean = true

  get form(): VForm {
    return (this.$refs as any).form
  }

  async submit() {
    if (this.form.validate()) {
      await API.post('OTMClientAPI', `/orgs/${this.currentOrg}/containers`, {
        body: { label: this.name },
      })
      await this.$router.push({
        name: 'orgs-name',
        params: { name: this.currentOrg },
      })
    }
  }
}
</script>

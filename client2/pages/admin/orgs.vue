<template>
  <v-container>
    <h2 class="mb-4">Orgs</h2>

    <v-simple-table class="mb-4">
      <thead>
        <tr>
          <th>Name</th>
          <th>Operation</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="org in orgs" :key="org.name">
          <td>{{ org.name }}</td>
          <td>
            <v-btn
              :to="{ name: 'orgs-name-setting', params: { name: org.name } }"
              >Setting</v-btn
            >
          </td>
        </tr>
      </tbody>
    </v-simple-table>
    <v-progress-linear v-if="isLoading" indeterminate />

    <v-btn v-if="next" class="mb-4" @click="loadNext">Load next</v-btn>

    <h2 class="mb-4">Create new org</h2>
    <v-form ref="form" v-model="newValid" @submit.prevent="createOrg">
      <v-row>
        <v-col>
          <v-text-field
            v-model="newOrgName"
            label="Name"
            aria-required="true"
            :rules="nameRules"
          />
        </v-col>
        <v-col>
          <v-btn :disabled="!newValid" type="submit">Save</v-btn>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script lang="ts">
import { API } from '@aws-amplify/api'
import { Component, Vue, Ref } from 'vue-property-decorator'
import { IOrg } from '~/utils/api/org'
import { PaginationItem } from '~/utils/api/paginationItem'
import VForm from '~/utils/VForm'

@Component
export default class AdminOrgs extends Vue {
  @Ref()
  form: VForm

  isLoading: boolean = false

  newOrgName: string = ''
  newValid: boolean = false
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

  orgs: IOrg[] = []
  next: string | null = null

  async load() {
    this.isLoading = true
    const data: PaginationItem<IOrg> = await API.get('OTMClientAPI', '/orgs')
    this.orgs = data.items
    this.next = data.next
    this.isLoading = false
  }

  async loadNext() {
    this.isLoading = true
    const data: PaginationItem<IOrg> = await API.get('OTMClientAPI', '/orgs', {
      queryStringParameters: { next: this.next },
    })
    this.orgs = [...this.orgs, ...data.items]
    this.next = data.next
    this.isLoading = false
  }

  async createOrg() {
    await API.post('OTMClientAPI', '/orgs', { body: { name: this.newOrgName } })
    this.form?.reset()
    await this.load()
  }

  async mounted() {
    await this.load()
  }
}
</script>

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
    <new-org-form @create="load" />
  </v-container>
</template>

<script lang="ts">
import { API } from '@aws-amplify/api'
import { Component, Vue } from 'vue-property-decorator'
import { IOrg } from '~/utils/api/org'
import { PaginationItem } from '~/utils/api/paginationItem'
import NewOrgForm from '~/components/NewOrgForm.vue'
@Component({
  components: { NewOrgForm },
})
export default class AdminOrgs extends Vue {
  isLoading: boolean = false

  orgs: IOrg[] = []
  next: string | null = null

  async load() {
    this.isLoading = true
    const data: PaginationItem<IOrg> = await API.get(
      'OTMClientAPI',
      '/orgs',
      {}
    )
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

  async mounted() {
    await this.load()
  }
}
</script>

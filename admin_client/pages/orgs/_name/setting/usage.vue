<template>
  <v-container>
    <h2 class="mb-2">Usage report</h2>
    <v-simple-table>
      <thead>
        <tr>
          <th>Month</th>
          <td>Athena Scan (bytes)</td>
          <td>Collect (numbers)</td>
          <td>Details</td>
        </tr>
      </thead>
      <tbody>
        <tr v-for="usage in usages" :key="usage.month">
          <td>
            {{ usage.month }}
          </td>
          <td>
            {{ usage.athena_scan_size }}
          </td>
          <td>
            {{ usage.collect_size }}
          </td>
          <td class="pa-4">
            <ul>
              <li
                v-for="detail in usage.details"
                :key="detail.type + detail.tid"
              >
                {{ detail.type }}({{ detail.tid }}): {{ detail.size }}
              </li>
            </ul>
          </td>
        </tr>
      </tbody>
    </v-simple-table>
    <v-progress-linear v-if="isLoading" indeterminate class="mb-4" />
    <v-btn v-if="next" @click="loadNext">Load next</v-btn>
  </v-container>
</template>

<script lang="ts">
import { Component } from 'nuxt-property-decorator'
import { API } from '@aws-amplify/api'
import Org from '~/components/Org'
import { IOrgUsage } from '~/utils/api/usage'
import { PaginationItem } from '~/utils/api/paginationItem'

@Component
export default class OrgsSettingUsage extends Org {
  isLoading: boolean = false

  usages: IOrgUsage[] = []
  next: string | null = null

  async load() {
    this.isLoading = true
    const data: PaginationItem<IOrgUsage> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/usages`,
      {}
    )
    this.usages = data.items
    this.next = data.next
    this.isLoading = false
  }

  async loadNext() {
    this.isLoading = true
    const data: PaginationItem<IOrgUsage> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/usages`,
      { queryStringParameters: { next: this.next } }
    )
    this.usages = [...this.usages, ...data.items]
    this.next = data.next
    this.isLoading = false
  }

  async mounted() {
    await this.load()
  }
}
</script>

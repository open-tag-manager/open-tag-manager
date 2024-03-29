<template>
  <v-container class="container-users" fluid>
    <div class="ml-auto datepicker">
      <v-dialog
        ref="datepicker"
        v-model="datepickerModal"
        :return-value.sync="date"
        persistent
        width="290px"
      >
        <template v-slot:activator="{ on, attrs }">
          <v-text-field
            v-model="formattedDate"
            label="Date"
            readonly
            v-bind="attrs"
            v-on="on"
          />
        </template>
        <v-date-picker v-model="date" no-title scrollable range :max="maxDate">
          <v-spacer />
          <v-btn text color="primary" @click="datepickerModal = false">
            Cancel
          </v-btn>
          <v-btn
            text
            color="primary"
            @click="
              $refs.datepicker.save(date)
              changeDate()
            "
          >
            OK
          </v-btn>
        </v-date-picker>
      </v-dialog>
    </div>

    <v-skeleton-loader v-if="isLoading" class="mx-auto" type="text@3" />

    <div v-else>
      <h3>UUID: {{ cid }}</h3>
      <div>
        User Agents:

        <ul>
          <li v-for="agent in userAgents" :key="agent">{{ agent }}</li>
        </ul>

        User ID:
        <ul>
          <li v-for="id in userIds" :key="id">{{ id }}</li>
        </ul>
      </div>
    </div>

    <v-text-field
      v-model="search"
      append-icon="mdi-magnify"
      label="Search"
      single-line
      hide-details
    />

    <v-data-table
      :headers="headers"
      :items="items"
      :loading="isLoading"
      sort-by="datetime"
      group-by="psid"
      :search="search"
      :items-per-page="-1"
      :show-group-by="false"
    />
  </v-container>
</template>

<script lang="ts">
import { Component } from 'nuxt-property-decorator'
import {
  format as dateFormat,
  parse as dateParse,
  sub as dateSub,
} from 'date-fns'
import { Watch } from 'vue-property-decorator'
import API from '@aws-amplify/api'
import { IContainerUserState } from '~/utils/api/container_users'
import OrgContainer from '~/components/OrgContainer'
import { IQueryResult, IQueryExecution } from '~/utils/api/query'
import { TableHeader } from '~/utils/api/table_header'

@Component
export default class UserDetail extends OrgContainer {
  isLoading: boolean = false

  datepickerModal: boolean = false
  date: string[] = [
    dateFormat(dateSub(new Date(), { weeks: 1 }), 'yyyy-MM-dd'),
    dateFormat(new Date(), 'yyyy-MM-dd'),
  ]

  items: IContainerUserState[] = []
  search: string = ''

  get cid(): string {
    return this.$route.params.cid
  }

  get formattedDate(): string {
    if (this.date && this.date.length > 1) {
      const date = [...this.date].sort()
      return `${date[0]}〜${date[1]}`
    }

    return ''
  }

  delay(seconds: number): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve()
      }, seconds)
    })
  }

  async fetchResult(id: string): Promise<IQueryResult<IContainerUserState>> {
    const result: IQueryResult<IContainerUserState> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/users/${this.cid}/query_result/${id}`,
      {}
    )
    if (result.state === 'SUCCEEDED') {
      return result
    }

    if (result.state === 'FAILED' || result.state === 'CANCELLED') {
      throw new Error('Failed to load')
    }

    await this.delay(1000)
    return this.fetchResult(id)
  }

  async load() {
    this.isLoading = true

    const date = [...this.date].sort()
    const execute: IQueryExecution = await API.post(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/users/${this.cid}/start_query`,
      {
        body: {
          stime: dateParse(date[0], 'yyyy-MM-dd', new Date()).getTime(),
          etime: dateParse(date[1], 'yyyy-MM-dd', new Date()).getTime(),
        },
      }
    )
    const result = await this.fetchResult(execute.execution_id)
    this.items = result.items

    this.isLoading = false
  }

  get maxDate(): string {
    return dateFormat(new Date(), 'yyyy-MM-dd')
  }

  get headers(): TableHeader[] {
    return [
      {
        text: 'DateTime',
        value: 'datetime',
        sortable: false,
      },
      {
        text: 'Event',
        value: 'state',
        sortable: false,
      },
      {
        text: 'PageTitle',
        value: 'dt',
        sortable: false,
      },
      {
        text: 'Page',
        value: 'dl',
        sortable: false,
      },
      {
        text: 'Session',
        value: 'psid',
        sortable: false,
      },
      {
        text: 'UserId',
        value: 'uid',
        sortable: false,
      },
    ]
  }

  async changeDate() {
    const date = [...this.date].sort()
    await this.$router.push({ query: { stime: date[0], etime: date[1] } })
  }

  @Watch('$route.query')
  async changeRouteQuery() {
    await this.$fetch()
  }

  async fetch() {
    if (this.$route.query.stime) {
      this.date[0] = this.$route.query.stime as string
    }
    if (this.$route.query.etime) {
      this.date[1] = this.$route.query.etime as string
    }

    await this.load()
  }

  get userAgents() {
    return [
      ...new Set(this.items.map((i) => decodeURIComponent(i.cs_user_agent))),
    ]
  }

  get userIds() {
    return [
      ...new Set(
        this.items.map((i) => {
          if (i.uid) {
            return `${i.uid} (verified=${i.is_verified})`
          }

          return null
        })
      ),
    ].filter((d) => d)
  }
}
</script>

<style lang="scss" scoped>
.container-users {
  .datepicker {
    max-width: 290px;
  }
}
</style>

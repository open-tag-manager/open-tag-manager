<template>
  <v-container class="container-users">
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

    <v-progress-linear v-if="isLoading" indeterminate />

    <v-data-table :headers="headers" :items="items" @click:row="clickRow" />
  </v-container>
</template>

<script lang="ts">
import { Component } from 'nuxt-property-decorator'
import API from '@aws-amplify/api'
import {
  parse as dateParse,
  format as dateFormat,
  sub as dateSub,
} from 'date-fns'
import { Watch } from 'vue-property-decorator'
import OrgContainer from '~/components/OrgContainer'
import { IQueryResult } from '~/utils/api/query'
import { IContainerUser } from '~/utils/api/container_users'
import { TableHeader } from '~/utils/api/table_header'

@Component
export default class Users extends OrgContainer {
  isLoading: boolean = false

  datepickerModal: boolean = false
  date: string[] = [
    dateFormat(dateSub(new Date(), { weeks: 1 }), 'yyyy-MM-dd'),
    dateFormat(new Date(), 'yyyy-MM-dd'),
  ]

  items: IContainerUser[] = []

  get formattedDate(): string {
    if (this.date && this.date.length > 1) {
      const date = [...this.date].sort()
      return `${date[0]}〜${date[1]}`
    }

    return ''
  }

  get maxDate(): string {
    return dateFormat(new Date(), 'yyyy-MM-dd')
  }

  get headers(): TableHeader[] {
    return [
      {
        text: 'User ID',
        value: 'cid',
        sortable: false,
      },
      {
        text: 'Count',
        value: 'c',
        sortable: false,
      },
    ]
  }

  delay(seconds: number): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve()
      }, seconds)
    })
  }

  async fetchResult(id: string): Promise<IQueryResult<IContainerUser>> {
    const result: IQueryResult<IContainerUser> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/users/query_result/${id}`,
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
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/users/start_query`,
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

  async changeDate() {
    const date = [...this.date].sort()
    await this.$router.push({ query: { stime: date[0], etime: date[1] } })
  }

  async clickRow(item) {
    const date = [...this.date].sort()
    await this.$router.push({
      name: `orgs-name-containers-container-users-cid`,
      params: {
        name: this.currentOrg,
        container: this.currentContainer,
        cid: item.cid,
      },
      query: {
        stime: date[0],
        etime: date[1],
      },
    })
  }

  @Watch('$route.query')
  async changeRouteQuery() {
    await this.$fetch()
  }

  async fetch() {
    if (this.$route.query.stime) {
      this.date[0] = this.$route.query.stime
    }
    if (this.$route.query.etime) {
      this.date[1] = this.$route.query.etime
    }

    await this.load()
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

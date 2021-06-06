<template>
  <v-form ref="form" class="mb-4" lazy-validation @submit.prevent="create">
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
          prepend-icon="mdi-calendar"
          readonly
          v-bind="attrs"
          v-on="on"
        />
      </template>
      <v-date-picker v-model="date" no-title scrollable range>
        <v-spacer />
        <v-btn text color="primary" @click="datepickerModal = false">
          Cancel
        </v-btn>
        <v-btn text color="primary" @click="$refs.datepicker.save(date)">
          OK
        </v-btn>
      </v-date-picker>
    </v-dialog>
    <v-text-field v-model="label" label="Label" />
    <v-btn
      type="submit"
      class="text-capitalize"
      color="primary"
      :disabled="!(date && date.length === 2)"
    >
      Create new stats
    </v-btn>
    <v-snackbar v-model="snackbar" right top>{{ snackbarMessage }}</v-snackbar>
  </v-form>
</template>

<script lang="ts">
import { Component, Vue, Emit, Ref, Prop } from 'vue-property-decorator'
import { API } from '@aws-amplify/api'
import { parse as parseDate } from 'date-fns'
import VForm from '~/utils/VForm'

@Component
export default class NewStatForm extends Vue {
  @Ref()
  form?: VForm

  @Prop({ type: String, required: true })
  orgName!: string

  @Prop({ type: String, required: true })
  containerName!: string

  isSubmitting: boolean = false

  datepickerModal: boolean = false
  date: string[] | null = null
  label: string = ''

  snackbar: boolean = false
  snackbarMessage: string = ''

  get formattedDate(): string {
    if (this.date && this.date.length > 1) {
      return `${this.date[0]}〜${this.date[1]}`
    }

    return ''
  }

  @Emit('create')
  async create() {
    if (!(this.date && this.date.length === 2)) {
      return
    }

    this.isSubmitting = true
    const body: Record<string, string | number> = {}

    body.stime = parseDate(this.date[0], 'yyyy-MM-dd', new Date()).getTime()
    body.etime = parseDate(this.date[1], 'yyyy-MM-dd', new Date()).getTime()
    if (this.label) {
      body.label = this.label
    }

    try {
      this.snackbar = true
      this.snackbarMessage = 'Submitting..'
      await API.post(
        'OTMClientAPI',
        `/orgs/${this.orgName}/containers/${this.containerName}/stats`,
        { body }
      )
      this.form?.reset()
      this.snackbarMessage = 'Done'
    } catch (e) {
      this.snackbarMessage = 'Error!'
    }
    this.isSubmitting = false
  }
}
</script>

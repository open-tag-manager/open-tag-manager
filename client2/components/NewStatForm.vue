<template>
  <v-form class="mb-4" lazy-validation @submit.prevent="create">
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
    <v-text-field label="Label" />
    <v-btn type="submit" class="text-capitalize"> Create new stats </v-btn>
  </v-form>
</template>

<script lang="ts">
import { Component, Vue, Emit } from 'vue-property-decorator'

@Component
export default class NewStatForm extends Vue {
  datepickerModal: boolean = false
  date: string[] | null = null

  get formattedDate(): string {
    if (this.date && this.date.length > 1) {
      return `${this.date[0]}〜${this.date[1]}`
    }

    return ''
  }

  @Emit('create')
  async create() {}
}
</script>

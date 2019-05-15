<template>
  <div class="container py-2">
    <h2>Container List</h2>

    <table class="table">
      <thead>
      <tr>
        <th>
          Name
        </th>
        <th>
          ID
        </th>
        <th>
          Created At
        </th>
        <th>
          Updated At
        </th>
        <th>
          Operations
        </th>
      </tr>
      </thead>

      <tbody>
      <tr v-for="container in containers" :key="container.name">
        <td>
          {{ container.label || container.name }}
        </td>
        <td>
          {{ container.name }}
        </td>
        <td>
          {{ container.created_at | date }}

        </td>
        <td>
          {{ container.updated_at | date }}
        </td>
        <td class="text-right">
          <b-button variant="primary" :to="{name: 'Container-Stat', params: {org: $route.params.org, name: container.name}}">Stats</b-button>

          <b-button variant="primary" :to="{name: 'Container-Setting', params: {org: $route.params.org, name: container.name}}">Setting</b-button>

          <button type="button" class="btn btn-danger" @click="deleteContainer(container.name)">Delete</button>
        </td>
      </tr>

      </tbody>
    </table>

    <h2>Make New Container</h2>
    <b-form @submit="createContainer">
      <b-form-group label="Name" label-for="name">
        <b-form-input id="name" type="text" :state="error ? false : ($v.newName.$dirty ? !$v.newName.$invalid : null)" required v-model.trim="newName" @input="$v.newName.$touch()"></b-form-input>
        <b-form-invalid-feedback :force-show="!!error">
          {{ error }}
        </b-form-invalid-feedback>
      </b-form-group>

      <b-button type="submit" variant="primary" :disabled="$v.newName.$invalid || isCreating">Submit</b-button>
    </b-form>
  </div>
</template>

<script>
  import moment from 'moment'

  import { validationMixin } from 'vuelidate'
  import { required } from 'vuelidate/lib/validators'

  export default {
    name: 'containers',
    mixins: [validationMixin],
    data () {
      return {
        containers: [],
        newName: '',
        error: '',
        isCreating: false
      }
    },
    validations: {
      newName: {
        required
      }
    },
    async created () {
      await this.loadContainers()
    },
    filters: {
      date (d) {
        return moment.unix(d).format('YYYY/MM/DD HH:mm:ss')
      }
    },
    methods: {
      async createContainer () {
        if (this.$v.newName.$invalid) {
          return
        }
        this.isCreating = true
        this.error = null
        try {
          await this.$Amplify.API.post('OTMClientAPI', `/orgs/${this.$route.params.org}/containers`, {
            body: {name: this.newName}
          })
          await this.loadContainers()
          this.newName = ''
          await new Promise((resolve) => {
            setTimeout(() => {
              this.$v.$reset()
              this.isCreating = false
              resolve()
            }, 100)
          })
        } catch (e) {
          this.isCreating = false
          if (e.response && e.response.status === 400) {
            this.error = e.response.data.error
          }
        }
      },
      async loadContainers () {
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers`)
        this.containers = data
      },
      async deleteContainer (name) {
        await this.$Amplify.API.del('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${name}`)
        await this.loadContainers()
      }
    }
  }
</script>

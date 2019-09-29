<template>
  <div class="container py-2">
    <h3>Set a new goal</h3>

    <form @submit.prevent="createGoal" class="form mb-2">
      <div class="form-group">
        <label for="goal-name">Name (Required)</label>
        <input id="goal-name" type="text" required class="form-control" v-model="newGoal.name">
      </div>

      <div class="form-group">
        <label for="goal-target">Target (Required)</label>
        <input id="goal-target" type="text" required class="form-control" v-model="newGoal.target">
      </div>

      <div class="form-group">
        <label for="goal-target-criteria">Target criteria</label>
        <b-form-select id="goal-target-criteria" v-model="newGoal.target_match">
          <option value="eq">Equal</option>
        </b-form-select>
      </div>

      <div class="form-group">
        <label for="goal-path">Path</label>
        <input id="goal-path" type="text" class="form-control" v-model="newGoal.path">
      </div>

      <div class="form-group">
        <label for="goal-path-criteria">Path criteria</label>
        <b-form-select id="goal-target-criteria" v-model="newGoal.path_match">
          <option value="eq">Equal</option>
        </b-form-select>
      </div>

      <button type="submit" class="btn btn-primary">Create</button>
    </form>

    <h3>Goals</h3>
    <div class="row">
      <div v-for="goal in goals" :key="goal.id" class="col-6">
        <div class="card mb-1">
          <div>
            TODO: graph
          </div>
          <div class="card-body">
            <div class="mb-1">
              <div>ID: {{goal.id}}</div>
              <div>Name: {{goal.name}}</div>
              <div>Target status: <code>{{goal.target}}</code> (<code>{{goal.target_match}}</code>)</div>
              <div v-if="goal.path">Target path: <code>{{goal.path}}</code> (<code>{{goal.path_match}}</code>)</div>
            </div>
            <button class="btn btn-danger btn-sm" @click="deleteGoal(goal)">Delete</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  const goalDefault = () => {
    return {
      name: null,
      target: null,
      target_match: 'eq',
      path: null,
      path_match: 'eq'
    }
  }

  export default {
    data () {
      return {
        newGoal: goalDefault(),
        goals: []
      }
    },
    async created () {
      await this.reloadGoals()
    },
    methods: {
      async reloadGoals () {
        const name = this.$route.params.name
        const goals = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${name}/goals`)
        this.goals = goals
      },
      async createGoal () {
        const name = this.$route.params.name
        await this.$Amplify.API.post('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${name}/goals`, {body: this.newGoal})
        this.newGoal = goalDefault()
        await this.reloadGoals()
      },
      async deleteGoal (goal) {
        const name = this.$route.params.name
        await this.$Amplify.API.del('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${name}/goals/${goal.id}`)
        await this.reloadGoals()
      }
    }
  }
</script>

<style scoped>
  .form {
    max-width: 500px;
  }

  .card {
    min-height: 200px;
  }
</style>

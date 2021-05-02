<template>
  <v-container>
    <v-expansion-panels class="panels mb-4">
      <v-expansion-panel>
        <v-expansion-panel-header>
          <h2>Set a new goal</h2>
        </v-expansion-panel-header>
        <v-expansion-panel-content>
          <v-form ref="form" lazy-validation @submit.prevent="save">
            <v-text-field
              v-model="newGoal.name"
              label="Name *"
              aria-required="true"
              :rules="nameRules"
            />
            <v-text-field
              v-model="newGoal.target"
              label="Target *"
              aria-required="true"
              :rules="targetRules"
            />
            <v-select
              v-model="newGoal.target_match"
              item-text="text"
              item-value="value"
              :items="matchItems"
              label="Target match condition"
            />
            <v-text-field v-model="newGoal.path" label="Path" />
            <v-select
              v-model="newGoal.path_match"
              item-text="text"
              item-value="value"
              :items="matchItems"
              label="Target match condition"
            />
            <v-text-field v-model="newGoal.label" label="Label" />
            <v-select
              v-model="newGoal.label_match"
              item-text="text"
              item-value="value"
              :items="matchItems"
              label="Target match condition"
            />
            <div class="text-right">
              <v-btn type="submit" color="primary"> Create </v-btn>
            </div>
          </v-form>
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>

    <h2>Goals</h2>
    <v-row v-if="goals">
      <v-col v-for="goal in goals" :key="goal.id" cols="6">
        <goal-result-card :goal="goal" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Vue, Component, Ref } from 'nuxt-property-decorator'
import API from '@aws-amplify/api'
import GoalResultCard from '@/components/GoalResultCard.vue'
import { IGoal } from '~/utils/api/goal'

@Component({
  components: { GoalResultCard },
})
export default class Goals extends Vue {
  @Ref() form?: any

  isLoading = false
  goals: IGoal[] | null = null

  nameRules = [(v: string) => !!v || 'Name is required']
  targetRules = [(v: string) => !!v || 'Target is required']

  newGoal: IGoal = {
    name: '',
    target: '',
    target_match: 'eq',
    path: null,
    path_match: 'eq',
    label: null,
    label_match: 'eq',
  }

  matchItems = [
    { text: 'Equal', value: 'eq' },
    { text: 'Prefix match', value: 'prefix' },
    { text: 'Regular expression match', value: 'regex' },
  ]

  async reloadGoals() {
    this.isLoading = true
    try {
      this.goals = await API.get(
        'OTMClientAPI',
        `/orgs/${this.$route.params.name}/containers/${this.$route.params.container}/goals`,
        {}
      )
    } catch (e) {
      // loading error
      console.log(e)
    } finally {
      this.isLoading = false
    }
  }

  save() {}

  async created() {
    await this.reloadGoals()
  }
}
</script>

<style scoped lang="scss">
.panels {
  max-width: 500px;
}
</style>

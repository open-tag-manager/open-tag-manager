<template>
  <v-card>
    <v-card-title>{{ goal.name }}</v-card-title>
    <v-card-text>
      <dl class="goal-config mb-4">
        <dt>ID</dt>
        <dd>
          <code>{{ goal.id }}</code>
        </dd>
        <dt>Target Status</dt>
        <dd>
          <code>{{ goal.target }}</code
          >(<code>{{ goal.target_match }}</code
          >)
        </dd>
        <template v-if="goal.path">
          <dt>Target Path</dt>
          <dd>
            <code>{{ goal.path }}</code
            >(<code>{{ goal.path_match }}</code
            >)
          </dd>
        </template>
        <template v-if="goal.label">
          <dt>Target Label</dt>
          <dd>
            <code>{{ goal.label }}</code
            >(<code>{{ goal.label_match }}</code
            >)
          </dd>
        </template>
      </dl>

      <v-card-actions>
        <v-btn>Recounting old data</v-btn>
        <v-btn color="error" @click="deleteGoal">Delete</v-btn>
      </v-card-actions>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Emit } from 'nuxt-property-decorator'
import { API } from '@aws-amplify/api'
import { IGoal } from '~/utils/api/goal'
import OrgContainer from '~/components/OrgContainer'

@Component
export default class GoalResultCard extends OrgContainer {
  @Prop({ required: true })
  goal!: IGoal

  created() {}

  @Emit('deleted')
  async deleteGoal() {
    await API.del(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/goals/${this.goal.id}`
    )
  }
}
</script>

<style scoped lang="scss">
.goal-config {
  display: grid;
  grid-template: auto / 10em 1fr;

  dt {
    grid-column: 1;
  }

  dd {
    grid-column: 2;
  }
}
</style>

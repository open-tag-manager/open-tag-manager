<template>
  <div>{{ goal.id }}</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'nuxt-property-decorator'
import { IGoal } from '~/utils/api/goal'

@Component
export default class GoalResultCard extends Vue {
  @Prop({ required: true })
  goal!: IGoal

  created() {}
}
</script>

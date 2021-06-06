<template>
  <v-card>
    <v-card-title>{{ goal.name }}</v-card-title>

    <div class="graph"></div>

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
        <v-btn @click="recountingModal = true">Recounting old data</v-btn>
        <v-btn color="error" @click="deleteGoal">Delete</v-btn>
      </v-card-actions>
    </v-card-text>

    <v-dialog v-model="recountingModal" max-width="350px">
      <v-form ref="recountingForm" @submit.prevent="recountingData">
        <v-card>
          <v-card-title>Recounting old data</v-card-title>
          <v-layout justify-center>
            <v-date-picker v-model="date" no-title scrollable range />
          </v-layout>
          <v-card-actions>
            <v-spacer />
            <v-btn
              type="submit"
              color="primary"
              :disabled="!date || date.length < 2"
              >Submit</v-btn
            >
          </v-card-actions>
        </v-card>
      </v-form>
    </v-dialog>
    <v-snackbar v-model="snackbar" right top>{{ snackbarMessage }}</v-snackbar>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Emit } from 'nuxt-property-decorator'
import { API } from '@aws-amplify/api'
import { select as d3select, pointer as d3pointer } from 'd3-selection'
import {
  extent as d3extent,
  max as d3max,
  bisector as d3bisector,
} from 'd3-array'
import { scaleTime as d3scaleTime, scaleLinear as d3scaleLiner } from 'd3-scale'
import axios from 'axios'
import { timeDays as d3timeDays } from 'd3-time'
import { timeFormat as d3timeFormat } from 'd3-time-format'
import { subDays, format as dateFormat, parse as dateParse } from 'date-fns'
import { axisLeft as d3axisLeft, axisBottom as d3axisBottom } from 'd3-axis'
import { line as d3line } from 'd3-shape'
import { IGoal, IGoalResultData } from '~/utils/api/goal'
import OrgContainer from '~/components/OrgContainer'

@Component
export default class GoalResultCard extends OrgContainer {
  @Prop({ required: true })
  goal!: IGoal

  recountingModal = false
  date: string[] | null = null
  snackbar = false
  snackbarMessage: string = ''

  async recountingData() {
    this.snackbar = true
    this.snackbarMessage = 'Submitting..'
    const date = this.date!.sort()
    await API.post(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/goals/${this.goal.id}/update_requests`,
      {
        body: {
          startdate: dateFormat(
            dateParse(date[0], 'yyyy-MM-dd', new Date()),
            'yyyyMMdd'
          ),
          enddate: dateFormat(
            dateParse(date[1], 'yyyy-MM-dd', new Date()),
            'yyyyMMdd'
          ),
        },
      }
    )
    this.snackbarMessage = 'Requested'
    this.recountingModal = false
    this.date = null
  }

  async mounted() {
    const componentElement = d3select(this.$el)
    const graphElement = componentElement.select('.graph')
    const width = (graphElement.node() as Element).clientWidth
    const margin = { left: 40, right: 10, top: 5, bottom: 30 }
    const height = 200
    const svg = graphElement.append('svg')
    svg.attr('width', width).attr('height', height)

    if (!this.goal.result_url) {
      return
    }

    const d = await axios.get<IGoalResultData[]>(this.goal.result_url)
    const data = d.data
    if (data.length === 0) {
      return
    }

    const formatTime = d3timeFormat('%Y-%m-%d')
    const dateRange = d3extent(data, (d) => new Date(d.date)) as [Date, Date]
    const newData = d3timeDays(subDays(dateRange[0], 1), dateRange[1]).map(
      (d) => {
        const date = formatTime(d)
        return (
          data.find((od) => od.date === date) || {
            date,
            e_count: 0,
            u_count: 0,
          }
        )
      }
    )

    const xScale = d3scaleTime()
      .domain(dateRange)
      .range([margin.left, width - margin.right])

    const yScale = d3scaleLiner()
      .domain([
        0,
        d3max(
          data.map((d) => {
            if (d.e_count < d.u_count) {
              return d.u_count
            }
            return d.e_count
          })
        ) as number,
      ])
      .range([height - margin.bottom, margin.top])

    const focus = svg
      .append('g')
      .append('circle')
      .style('fill', 'none')
      .style('stroke', 'black')
      .style('r', 3)
      .style('opacity', 0)
    const focusText = graphElement
      .append('div')
      .attr('class', 'focus-text')
      .style('opacity', 0)
      .style('text-align', 'center')
      .style('position', 'absolute')
      .style('z-index', 255)

    const bisect = d3bisector((d: IGoalResultData) => {
      return new Date(d.date)
    })

    svg
      .append('rect')
      .style('fill', 'none')
      .style('pointer-events', 'all')
      .attr('width', width)
      .attr('height', height)
      .on('mouseover', () => {
        focus.style('opacity', 1)
        focusText.style('opacity', 0.5)
      })
      .on('mouseout', () => {
        focus.style('opacity', 0)
        focusText.style('opacity', 0)
      })
      .on('mousemove', function (event) {
        let d = null
        if (newData.length > 1) {
          const x0 = xScale.invert(d3pointer(event)[0])
          const i = bisect.center(newData, x0, 1)
          if (i < newData.length) {
            const d0 = newData[i - 1]
            const d1 = newData[i]
            d =
              x0.getTime() - new Date(d0.date).getTime() >
              new Date(d1.date).getTime() - x0.getTime()
                ? d1
                : d0
          } else {
            d = newData[newData.length - 1]
          }
        } else if (newData.length === 1) {
          d = newData[0]
        }
        if (d) {
          focus
            .attr('cx', xScale(new Date(d.date)))
            .attr('cy', yScale(d.e_count))
          focusText
            .html(d.date + ' ' + d.e_count)
            .style('left', xScale(new Date(d.date)) + 'px')
            .style('top', yScale(d.e_count) - 20 + 'px')
        }
      })
    svg
      .append('path')
      .datum(newData)
      .attr('fill', 'none')
      .attr('stroke', 'steelblue')
      .attr('stroke-width', 1.5)
      .attr(
        'd',
        d3line<IGoalResultData>()
          .x((d) => {
            return xScale(new Date(d.date))
          })
          .y((d) => {
            return yScale(d.e_count)
          })
      )
    svg
      .append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(${[0, height - margin.bottom].join(',')})`)
      .call(
        d3axisBottom(xScale).tickFormat(
          d3timeFormat('%m/%d') as (
            dv: number | Date | { valueOf(): number },
            i: number
          ) => string
        )
      )
    svg
      .append('g')
      .attr('class', 'y-axis')
      .attr('transform', `translate(${[margin.left, 0].join(',')})`)
      .call(d3axisLeft(yScale))
    if (newData.length > 0) {
      svg.append('text').text(newData[newData.length - 1].e_count)
    }
  }

  @Emit('deleted')
  async deleteGoal() {
    await API.del(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/goals/${this.goal.id}`,
      {}
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

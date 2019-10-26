<template>
  <div class="card mb-1">
    <div class="graph"></div>
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
</template>

<script>
  import axios from 'axios'
  import * as d3 from 'd3'

  export default {
    props: {
      goal: {
        type: Object,
        required: true
      }
    },
    async mounted () {
      const componentElement = d3.select(this.$el)
      const graph = componentElement.select('.graph')
      const width = graph.node().clientWidth
      const margin = {left: 0, right: 0, top: 0, bottom: 50}
      const height = 200
      const svg = graph.append('svg')
      svg.attr('width', width).attr('height', height)
      const d = await axios.get(this.goal.result_url)
      const data = d.data

      const xScale = d3.scaleTime()
        .domain([d3.min(data.map((d) => {
          return new Date(d.date)
        })), d3.max(data.map((d) => {
          return new Date(d.date)
        }))])
        .range([0, width])

      const yScale = d3.scaleLinear()
        .domain([0, d3.max(data.map((d) => {
          if (d.e_count < d.u_count) {
            return d.e_count
          }
          return d.u_count
        }))])
        .range([height - margin.bottom, margin.top])

      const focus = svg.append('g')
        .append('circle')
        .style('fill', 'none')
        .style('stroke', 'black')
        .style('r', 3)
        .style('opacity', 0)

      const focusText = graph.append('div')
        .attr('class', 'focus-text')
        .style('opacity', 0)
        .style('text-align', 'center')
        .style('position', 'absolute')
        .style('z-index', 255)

      const bisect = d3.bisector((d) => {
        return d.x
      }).left

      svg.append('rect')
        .style('fill', 'none')
        .style('pointer-events', 'all')
        .attr('width', width - margin.left - margin.right)
        .attr('height', height - margin.top - margin.bottom)
        .on('mouseover', () => {
          focus.style('opacity', 1)
          focusText.style('opacity', 0.5)
        })
        .on('mouseout', () => {
          focus.style('opacity', 0)
          focusText.style('opacity', 0)
        })
        .on('mousemove', function () {
          const x0 = xScale.invert(d3.mouse(this)[0])
          const i = bisect(data, x0, 1)
          const selectedData = data[i]
          focus.attr('cx', xScale(new Date(selectedData.date)))
            .attr('cy', yScale(selectedData.e_count))
          focusText.html(selectedData.date + ' ' + selectedData.e_count)
            .style('left', xScale(new Date(selectedData.date)) + 'px')
            .style('top', yScale(selectedData.e_count) - 20 + 'px')
        })

      svg.append('path').datum(data)
        .attr('fill', 'none')
        .attr('stroke', 'steelblue')
        .attr('stroke-width', 1.5)
        .attr('d', d3.line()
          .x((d) => {
            return xScale(new Date(d.date))
          })
          .y((d) => {
            return yScale(d.e_count)
          })
        )

      svg.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(${[0, height - margin.bottom].join(',')})`)
        .call(d3.axisBottom(xScale).tickFormat(d3.timeFormat('%m/%d')))

      if (data.length > 0) {
        svg.append('text').text(data[data.length - 1].e_count)
      }
    },
    methods: {
      async deleteGoal (goal) {
        const name = this.$route.params.name
        await this.$Amplify.API.del('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${name}/goals/${goal.id}`)
        await this.reloadGoals()
      }
    }
  }
</script>

<style scoped>
  .graph {
    position: relative;
  }
</style>

<style>
  .graph .focus-text {
    width: 100px;
    font-size: 8px;
    color: white;
    background-color: #000000;
    border-radius: 5px;
  }
</style>

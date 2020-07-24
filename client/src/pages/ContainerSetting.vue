<template>
  <div class="container py-2">
    <div v-if="container">
      <h2>{{container.label || container.name}}'s configuration</h2>

      <div>
        Script URL: <input type="text" readonly v-model="container.script" class="form-control">
        <textarea readonly class="form-control" v-model="tag"></textarea>
      </div>

      <form @submit.prevent="save">
        <h3 class="my-2">Container config</h3>

        <div class="form-group">
          <label for="container-name">Name</label>
          <input id="container-name" type="text" class="form-control" required v-model="label">
        </div>

        <div class="form-group">
          <label for="container-domain">Site domains (comma separated)</label>
          <input id="container-domain" type="text" class="form-control" v-model.trim="siteDomains">
        </div>

        <button type="submit" class="btn btn-primary">Save</button>
      </form>

      <hr>

      <form @submit.prevent="deploy">
        <b-button variant="primary" class="my-2" type="submit">Deploy container</b-button>

        <h3 class="my-2">Observers</h3>

        <b-card v-for="observer in container.observers" :key="observer.id" class="my-2">
          <div class="form-group">
            <label :for="observer.id + '_trigger'">Trigger</label>
            <b-form-select v-model="observer.target" required>
              <option v-for="trigger in triggers" :value="trigger.id" :key="trigger.id">
                {{trigger.name}}
              </option>
            </b-form-select>
          </div>

          <div class="form-group" v-if="observer.target === 'custom'">
            <label :for="observer.id + '_event'">Custom Target</label>
            <input type="text" :id="observer.id + '_event'" v-model="observer.custom" class="form-control" required>
          </div>

          <div class="form-group" v-if="getTriggerById(observer.target).tag">
            <label :for="observer.id + '_tag'">Trigger Target Tag</label>
            <input type="text" :id="observer.id + '_tag'" v-model="observer.options.tag" class="form-control">
          </div>

          <div class="form-group">
            <label :for="observer.id + '_name'">Name</label>
            <input class="form-control" :id="observer.id + '_name'" type="text" required v-model="observer.name">
          </div>

          <div class="form-group">
            <label :for="observer.id + '_type'">Action Type</label>
            <b-form-select v-model="observer.type" required @input="inputType(observer)">
              <option v-for="action in actionTypes" :key="action.id" :value="action.id">{{action.name}}</option>
            </b-form-select>
          </div>

          <div class="form-group" v-if="observer.type === 'load-script'">
            <label :for="observer.id + '_value'">Script URL</label>
            <input :id="observer.id + '_value'" v-model="observer.options.src" class="form-control" required type="url">
          </div>

          <div class="form-group" v-if="observer.type === 'html' || observer.type === 'script'">
            <label :for="observer.id + '_value'">{{ observer.type === 'html' ? 'HTML Tag' : 'Script' }}</label>
            <textarea :id="observer.id + '_value'" v-model="observer.options.script" class="form-control">
            </textarea>
          </div>

          <div v-if="observer.actionData && observer.actionData.params">
            <div class="form-group" v-for="p in observer.actionData.params">
              <label>{{p.label}}</label>
              <input type="text" v-model="observer.options[p.name]" class="form-control" :required="p.required">
            </div>
          </div>

          <b-checkbox v-model="observer.options.pageview"
                      v-if="observer.type === 'collect' && observer.target !== 'pageview'">Pageview event
          </b-checkbox>
          <b-checkbox v-model="observer.once">Once only</b-checkbox>

          <div class="my-2">
            <b-button variant="danger" @click="deleteObserver(observer)">Delete</b-button>
          </div>
        </b-card>

        <b-button variant="primary" @click="addBlankObserver">New Observer</b-button>

        <h3 class="my-2">Triggers</h3>

        <b-card v-for="trigger in container.triggers" :key="trigger.id" class="my-2">
          <div class="form-group">
            <label :for="trigger.id + '_name'">Name</label>
            <input class="form-control" :id="trigger.id + '_name'" type="text" required v-model="trigger.name">
          </div>

          <div class="form-group">
            <label :for="trigger.id + '_type'">Name</label>
            <b-form-select v-model="trigger.type" required @input="resetTriggerOption(trigger)">
              <option v-for="type in triggerTypes" :value="type.name" :key="type.name">
                {{type.name}}
              </option>
            </b-form-select>
          </div>

          <div class="form-group" v-for="field in getTriggerTypeByName(trigger.type).fields">
            <label :for="trigger.id + '_field_' + field.name">{{field.name}}</label>
            <input :type="field.type" class="form-control" v-model="trigger.options[field.name]">
          </div>

          <div class="my-2">
            <b-button variant="danger" @click="deleteTrigger(trigger)">Delete</b-button>
          </div>
        </b-card>

        <b-button variant="primary" @click="addBlankTrigger">New Trigger</b-button>
      </form>

      <hr>

      <form @submit.prevent="saveSwaggerDoc">
        <div class="form-group">
          <label for="swagger-doc">Swagger Doc (JSON)</label>
          <textarea id="swagger-doc" class="form-control" v-model="swaggerDoc" rows="10">
          </textarea>
        </div>
        <button type="submit" class="btn btn-primary">Save SwaggerDoc</button>
      </form>
    </div>
    <div v-else>
      Loading...
    </div>
  </div>
</template>

<script>
  import uuid from 'uuid/v4'
  import _ from 'lodash'

  export default {
    data () {
      return {
        label: null,
        siteDomains: null
      }
    },
    computed: {
      container () {
        return this.$store.state.container.container
      },
      triggers () {
        const preset = [
          {
            id: 'pageview',
            name: 'pageview'
          },
          {
            id: 'click',
            name: 'click',
            tag: true
          },
          {
            id: 'touchstart',
            name: 'touchstart',
            tag: true
          },
          {
            id: 'change-url',
            name: 'change-url'
          },
          {
            id: 'custom',
            name: 'custom'
          }
        ]
        return preset.concat(this.container.triggers)
      },
      actionTypes () {
        const preset = [
          {
            id: 'html',
            name: 'HTML'
          },
          {
            id: 'load-script',
            name: 'Load Script'
          },
          {
            id: 'collect',
            name: 'Collect'
          },
          {
            id: 'script',
            name: 'Script'
          }
        ]
        return [...preset, ...process.env.OTM_PLUGIN_ACTIONS]
      },
      triggerTypes () {
        return [
          {
            name: 'timer',
            fields: [
              {name: 'second', type: 'number', default: 10}
            ]
          },
          {
            name: 'scroll',
            fields: [
              {name: 'threshold', type: 'number', default: 10},
              {name: 'interval', type: 'number', default: 1}
            ]
          }
        ]
      },
      tag () {
        return '<script src="' + this.container.script + '"><' + '/script>'
      },
      swaggerDoc: {
        get () {
          return this.$store.state.container.editableSwaggerDoc
        },
        set (v) {
          this.$store.dispatch('container/editSwaggerDoc', {swaggerDoc: v})
        }
      }
    },
    async created () {
      await this.$store.dispatch('container/fetchContainer', {container: this.$route.params.name, org: this.$route.params.org})
      this.label = this.container.label
      const domains = this.container.domains
      if (Array.isArray(domains)) {
        this.siteDomains = domains.join(',')
      }
    },
    methods: {
      getTriggerById (id) {
        return _.find(this.triggers, (trigger) => {
          return trigger.id === id
        })
      },
      getTriggerTypeByName (name) {
        return _.find(this.triggerTypes, (type) => {
          return type.name === name
        })
      },
      addBlankObserver () {
        this.container.observers.push({
          id: uuid(),
          target: 'pageview',
          name: '',
          type: 'script',
          once: false,
          options: {}
        })
      },
      deleteObserver (observer) {
        this.container.observers = _.reject(this.container.observers, {id: observer.id})
      },
      resetTriggerOption (trigger) {
        const type = this.getTriggerTypeByName(trigger.type)
        trigger.options = {}
        for (let field of type.fields) {
          trigger.options[field.name] = field.default
        }
      },
      addBlankTrigger () {
        const trigger = {
          id: uuid(),
          type: 'timer',
          options: {}
        }
        this.container.triggers.push(trigger)
        this.resetTriggerOption(trigger)
      },
      deleteTrigger (trigger) {
        const observers = _.filter(this.container.observers, {
          target: trigger.id
        })
        if (observers.length > 0) {
          alert('You cannot delete this trigger because it used by any observers.')
          return
        }
        this.container.triggers = _.reject(this.container.triggers, {id: trigger.id})
      },
      async deploy () {
        await this.$store.dispatch('container/saveContainer', {
          observers: this.container.observers,
          triggers: this.container.triggers
        })
      },
      async save () {
        await this.$store.dispatch('container/saveContainer', {
          label: this.label,
          domains: this.siteDomains.split(',').filter(d => d)
        })
      },
      async saveSwaggerDoc () {
        await this.$store.dispatch('container/saveSwaggerDoc')
      },
      inputType (observer) {
        const action = this.getAction(observer.type)
        observer.actionData = action
      },
      getAction (id) {
        return this.actionTypes.find((type) => {
          return type.id === id
        })
      }
    }
  }
</script>

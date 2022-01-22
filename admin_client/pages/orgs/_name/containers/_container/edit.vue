<template>
  <v-container>
    <div v-if="container">
      <h1 class="mb-4">{{ container.label }}'s configuration</h1>
      <v-text-field v-model="container.script" readonly label="Script URL" />
      <v-text-field :value="scriptTag" readonly label="Script Tag" />
      <v-text-field
        :value="container.hash_key"
        :type="showHashKey ? 'text' : 'password'"
        readonly
        label="Hash Key (Keep secret)"
        :append-icon="showHashKey ? 'mdi-eye' : 'mdi-eye-off'"
        @click:append="() => (showHashKey = !showHashKey)"
      />
      <v-form ref="form" lazy-validation @submit.prevent="save">
        <h2 class="mb-4">Basic configuration</h2>
        <v-text-field
          v-model.trim="label"
          label="Label"
          aria-required="true"
          :rules="labelRules"
        />
        <v-text-field
          v-model.trim="domains"
          label="Site domains (comma separeted)"
        />

        <h2 class="mb-4">Observers</h2>

        <v-card
          v-for="observer in container.observers"
          :key="observer.id"
          class="mb-2"
        >
          <v-card-text>
            {{ observer.id }}
            <v-select
              v-model="observer.target"
              :items="triggers"
              item-text="name"
              item-value="id"
              label="Trigger"
            />
            <v-text-field
              v-if="observer.target === 'custom'"
              v-model="observer.custom"
              label="Custom Target"
              aria-required="true"
              :rules="customRules"
            />
            <v-text-field
              v-if="getTriggerById(observer.target).tag"
              v-model="observer.options.tag"
              label="Trigger Target Tag"
            />
            <v-text-field
              v-model="observer.name"
              label="Name"
              aria-required="true"
              :rules="nameRules"
            />

            <v-select
              v-model="observer.type"
              :items="actionTypes"
              item-text="name"
              item-value="id"
              label="Action Type"
            />
            <v-text-field
              v-if="observer.type === 'load-script'"
              v-model="observer.options.src"
              label="Script URL"
              aria-required="true"
              :rules="scriptRules"
            />
            <v-textarea
              v-if="observer.type === 'html' || observer.type === 'script'"
              v-model="observer.options.script"
              label="Script"
              :rules="scriptRules"
              aria-required="true"
            />

            <div v-if="observer.actionData && observer.actionData.params">
              <v-text-field
                v-for="p in observer.actionData.params"
                :key="p.name"
                v-model="observer.options[p.name]"
                :label="p.label"
                :aria-required="p.required"
                :rules="actionDataParamRule(p)"
              />
            </div>

            <v-checkbox
              v-if="
                observer.type === 'collect' && observer.target !== 'pageview'
              "
              v-model="observer.options.pageview"
              label="Pageview event"
            />

            <v-checkbox v-model="observer.once" label="Once only" />
          </v-card-text>
          <v-card-actions>
            <v-btn color="error" @click="deleteObserver(observer)">
              Delete
            </v-btn>
          </v-card-actions>
        </v-card>

        <v-btn class="text-capitalize my-4" @click="addNewObserver">
          <v-icon>mdi-plus</v-icon>Add New Observer
        </v-btn>

        <h2 class="mb-4">Triggers</h2>

        <v-card
          v-for="trigger in container.triggers"
          :key="trigger.id"
          class="mb-2"
        >
          <v-card-text>
            {{ trigger.id }}

            <v-text-field
              v-model="trigger.name"
              label="Name"
              :rules="nameRules"
              :aria-required="true"
            />
            <v-select
              v-model="trigger.type"
              label="Type"
              :items="triggerTypes"
              item-value="name"
              item-text="name"
              @change="resetTriggerOption(trigger)"
            />
            <v-text-field
              v-for="field in getTriggerTypeByName(trigger.type).fields"
              :key="field.name"
              v-model="trigger.options[field.name]"
              :label="field.name"
              :type="field.type"
            />
          </v-card-text>
          <v-card-actions>
            <v-btn color="error" @click="deleteTrigger(trigger)">
              Delete
            </v-btn>
          </v-card-actions>
        </v-card>

        <v-btn class="text-capitalize my-4" @click="addNewTrigger">
          <v-icon>mdi-plus</v-icon>Add New Trigger
        </v-btn>

        <div>
          <v-btn type="submit">Save</v-btn>
        </div>
      </v-form>
    </div>
    <v-skeleton-loader v-else type="card" />
    <v-snackbar v-model="snackbar" right top>{{ snackbarMessage }}</v-snackbar>
  </v-container>
</template>

<script lang="ts">
import API from '@aws-amplify/api'
import { Component, Ref } from 'vue-property-decorator'
import { v4 as uuid } from 'uuid'
import OrgContainer from '~/components/OrgContainer'
import {
  IContainer,
  IContainerObserver,
  IContainerTrigger,
  IContainerTriggerType,
} from '~/utils/api/container'
import VForm from '~/utils/VForm'

@Component
export default class ContainerEdit extends OrgContainer {
  @Ref() form?: VForm

  container: IContainer | null = null
  label: string = ''
  domains: string = ''

  labelRules = [(v: any) => !!v || 'Label is required']
  customRules = [(v: any) => !!v || 'Custom Target is required']
  nameRules = [(v: any) => !!v || 'Name is required']
  scriptRules = [(v: any) => !!v || 'Script is required']

  snackbarMessage: string = ''
  snackbar: boolean = false

  showHashKey: boolean = false

  actionDataParamRule(p: any) {
    if (p && p.required) {
      return [(v: any) => !!v || 'Required']
    }

    return []
  }

  get triggers(): IContainerTrigger[] {
    const preset: IContainerTrigger[] = [
      {
        id: 'init',
        name: 'init',
      },
      {
        id: 'pageview',
        name: 'pageview',
      },
      {
        id: 'click',
        name: 'click',
        tag: true,
      },
      {
        id: 'touchstart',
        name: 'touchstart',
        tag: true,
      },
      {
        id: 'change-url',
        name: 'change-url',
      },
      {
        id: 'custom',
        name: 'custom',
      },
    ]
    if (this.container?.triggers) {
      return [...preset, ...this.container.triggers]
    }

    return preset
  }

  get triggerTypes(): IContainerTriggerType[] {
    return [
      {
        name: 'timer',
        fields: [{ name: 'second', type: 'number', default: 10 }],
      },
      {
        name: 'scroll',
        fields: [
          { name: 'threshold', type: 'number', default: 10 },
          { name: 'interval', type: 'number', default: 1 },
        ],
      },
    ]
  }

  get actionTypes(): object[] {
    const preset: object[] = [
      {
        id: 'html',
        name: 'HTML',
      },
      {
        id: 'load-script',
        name: 'Load Script',
      },
      {
        id: 'collect',
        name: 'Collect',
      },
      {
        id: 'script',
        name: 'Script',
      },
    ]

    return preset
  }

  get scriptTag() {
    if (this.container?.script) {
      // eslint-disable-next-line no-useless-escape
      return `<script src="${this.container.script}" async><\/script>`
    }

    return ''
  }

  async load() {
    const container: IContainer = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}`,
      {}
    )
    this.container = container
    this.label = container.label
    this.domains = container.domains.join(',')
  }

  addNewObserver() {
    if (!this.container) {
      return
    }
    const newObserver: IContainerObserver = {
      id: uuid(),
      target: 'pageview',
      name: '',
      type: 'script',
      once: false,
      options: {},
    }
    this.container.observers.push(newObserver)
  }

  deleteObserver(observer: IContainerObserver) {
    if (!this.container) {
      return
    }

    this.container.observers = this.container.observers.filter(
      (o) => o.id !== observer.id
    )
  }

  getTriggerById(id: string): IContainerTrigger | undefined {
    return this.triggers.find((t) => t.id === id)
  }

  getTriggerTypeByName(name: string): IContainerTriggerType | undefined {
    return this.triggerTypes.find((t) => t.name === name)
  }

  resetTriggerOption(trigger: IContainerTrigger) {
    if (!trigger.type) {
      return
    }
    const type = this.getTriggerTypeByName(trigger.type)
    trigger.options = {}
    if (!type?.fields) {
      return
    }
    for (const field of type.fields) {
      trigger.options[field.name] = field.default
    }
  }

  addNewTrigger() {
    if (!this.container) {
      return
    }
    const id = uuid()
    const newTrigger: IContainerTrigger = {
      id,
      name: id,
      type: 'timer',
      options: {},
    }
    this.resetTriggerOption(newTrigger)
    this.container.triggers.push(newTrigger)
  }

  deleteTrigger(trigger: IContainerTrigger) {
    if (!this.container) {
      return
    }
    const observers = this.container.observers.filter(
      (o) => o.target === trigger.id
    )
    if (observers.length > 0) {
      this.snackbarMessage =
        'You cannot delete this trigger because it used by any observers.'
      this.snackbar = true
      return
    }
    this.container.triggers = this.container.triggers.filter(
      (t) => t.id !== trigger.id
    )
  }

  async save() {
    if (this.container && this.form && this.form.validate()) {
      await API.put(
        'OTMClientAPI',
        `/orgs/${this.currentOrg}/containers/${this.currentContainer}`,
        {
          body: {
            label: this.label,
            domains: this.domains.split(',').filter((d) => d),
            observers: this.container.observers,
            triggers: this.container.triggers,
          },
        }
      )
      this.snackbarMessage = 'Saved'
      this.snackbar = true
      await this.load()
    }
  }

  async created() {
    await this.load()
  }
}
</script>

export interface IContainerObserver {
  id: string
  once: boolean
  name: string
  type: string
  target: string
  options: any
  custom?: string
  actionData?: any
}

export interface IContainerTrigger {
  id: string
  name?: string
  type?: string
  tag?: boolean
  options?: any
}

export interface IContainerTriggerTypeField {
  name: string
  type: string
  default?: string | number
}

export interface IContainerTriggerType {
  name: string
  fields: IContainerTriggerTypeField[]
}

export interface IContainer {
  // eslint-disable-next-line camelcase
  created_at: number
  // eslint-disable-next-line camelcase
  updated_at: number
  // eslint-disable-next-line camelcase
  swagger_doc: object
  tid: string
  organization: string | undefined
  observers: IContainerObserver[]
  triggers: IContainerTrigger[]
  script: string | null
  label: string
  domains: string[]
}

import Cookies from 'js-cookie'
import {WebCollector} from '@open-tag-manager/web-collector'
import uuidV4 from 'uuid/v4'
import JsSHA from 'jssha'
import url from 'url'
import template from 'lodash.template'
import {getCLS, getFID, getLCP} from 'web-vitals'

if ('PerformanceLongTaskTiming' in window) {
  let g = window.__tti = {e: []}
  g.o = new PerformanceObserver(function (l) {
    g.e = g.e.concat(l.getEntries())
  })
  g.o.observe({entryTypes: ['longtask']})
}

class OTM {
  constructor () {
    this.observers = []
  }

  addObserver (target, func) {
    this.observers.push({target: target, func: func})
  }

  notify (target, params = {}) {
    const observers = this.observers.filter((observer) => {
      return observer.target === target || (observer.target === 'custom' && observer.custom === target)
    })
    for (let observer of observers) {
      if (observer.options.tag && observer.options.tag !== params.o_tag) {
        // skip notify event, because there is tag criteria
        return
      }

      if (observer.isNotified && observer.once) {
        continue
      }

      let type = observer.type
      let options = observer.options
      if (observer && observer.actionData && observer.actionData.base) {
        type = observer.actionData.base
        for (let templateName in observer.actionData.template) {
          options[templateName] = template(observer.actionData.template[templateName])(observer.options)
        }
      }

      switch (type) {
        case 'html':
          const fragment = document.createRange().createContextualFragment(options.script)
          let node = fragment.firstChild
          while (node) {
            document.body.appendChild(node)
            node = fragment.firstChild
          }
          break
        case 'collect':
          // manage state for collect
          this.prevTime = (new Date()).getTime()
          this.prevState = this.state
          let newState = options.pageview ? 'pageview' : target
          if (newState !== 'pageview') {
            if (params.statePrefix) {
              newState = params.statePrefix + '_' + newState
              delete params.statePrefix
            }
            if (params.stateSuffix) {
              newState += '_' + params.stateSuffix
              delete params.stateSuffix
            }
          } else {
            if (options.pageview && this.prevState.match(/^click_widget_/)) {
              params.plt = (new Date()).getTime() - this.prevTime
            }
          }
          this.state = newState
          Cookies.set('_st', newState, {expires: 20})

          for (let n in observer.collect) {
            params[n] = observer.collect[n]
          }
          if (this.org) {
            params['org'] = this.org
          }
          this.call(observer.name, options.pageview ? 'pageview' : target, params)

          this.prevUrl = this.url
          Cookies.set('_pu', window.document.URL, {expires: 20})

          break
        case 'script':
          const bindParams = Object.assign({name: observer.name, target}, params)
          if (typeof options.script === 'function') {
            options.script(bindParams)
          } else {
            // eslint-disable-next-line no-eval
            const func = eval('(function(params){' + options.script + '})')
            func(bindParams)
          }
          break
        case 'load-script':
          this.loadScript(options.src, {})
          break
      }

      observer.isNotified = true
    }
  }

  performance (category, variable, time, params = {}) {
    if (this.preview) {
      console.log('performance', name, params)
      return
    }
    const collectParams = Object.assign({}, params)
    collectParams.dt = document.title.substring(0, 120)
    collectParams.o_cts = (new Date()).getTime()
    collectParams.o_psid = this.viewUUID
    collectParams.o_ps = this.prevState
    collectParams.o_r = uuidV4()
    this.webCollector.timing(category, variable, time, collectParams)
  }

  call (name, target, params = {}) {
    if (this.preview) {
      console.log('call', name, target, params)
      return
    }

    const collectParams = Object.assign({}, params)
    collectParams.dt = document.title.substring(0, 120)
    collectParams.o_cts = (new Date()).getTime()
    collectParams.o_pl = this.prevUrl
    collectParams.o_psid = this.viewUUID
    collectParams.o_ps = this.prevState
    collectParams.o_s = this.state
    collectParams.o_r = uuidV4()
    if (this.uid) {
      collectParams.uid = this.uid
    }
    if (target === 'pageview') {
      this.webCollector.pageview(collectParams)
    } else {
      this.webCollector.event(target, name, null, collectParams)
    }
  }

  _scrollTop (targetElement = null) {
    if (targetElement) {
      return targetElement.scrollTop
    }

    let document
    let body

    return (
      'pageYOffset' in window
        ? window.pageYOffset
        : ((document = window.document).documentElement || (body = document.body).parentNode || body).scrollTop
    )
  }

  _scrollLeft (targetElement = null) {
    if (targetElement) {
      return targetElement.scrollLeft
    }

    let document
    let body

    return (
      'pageXOffset' in window
        ? window.pageXOffset
        : ((document = window.document).documentElement || (body = document.body).parentNode || body).scrollLeft
    )
  }

  _getXpathByElementNode (eNode) {
    const NODE_TYPE_ELEMENT_NODE = 1

    if (eNode instanceof Array) {
      eNode = eNode[0]
    }

    if (eNode.nodeType !== NODE_TYPE_ELEMENT_NODE) {
      return ''
    }

    const stacker = []
    let nodeName = ''
    let nodeCount = 0
    let nodePoint = null

    do {
      if (!eNode || !eNode.parentNode || !eNode.parentNode.children) {
        break
      }

      nodeName = eNode.nodeName.toLowerCase()
      if (eNode.parentNode.children.length > 1) {
        nodeCount = 0
        nodePoint = null
        for (let i = 0; i < eNode.parentNode.children.length; i++) {
          if (eNode.nodeName === eNode.parentNode.children[i].nodeName) {
            nodeCount++
            if (eNode === eNode.parentNode.children[i]) {
              nodePoint = nodeCount
            }
            if (nodePoint != null && nodeCount > 1) {
              nodeName += '[' + nodePoint + ']'
              break
            }
          }
        }
      }
      stacker.unshift(nodeName)
    } while ((eNode = eNode.parentNode) !== null && eNode.nodeName !== '#document')

    return '/' + stacker.join('/').toLowerCase()
  }

  _getWidgetElement (eNode) {
    const NODE_TYPE_ELEMENT_NODE = 1

    if (eNode instanceof Array) {
      eNode = eNode[0]
    }

    if (eNode.nodeType !== NODE_TYPE_ELEMENT_NODE) {
      return null
    }

    do {
      if (!eNode) {
        return false
      }

      let nodeName = eNode.nodeName.toLowerCase()
      if (nodeName === 'a' || nodeName === 'button') {
        return eNode
      }

      if (eNode.style.cursor && eNode.style.cursor === 'pointer') {
        return eNode
      }

      if (eNode.attributes) {
        for (let attribute of eNode.attributes) {
          let attributeName = attribute.name.toLowerCase()
          if (attributeName === 'onclick' || attributeName === 'ng-click' || attributeName === '@click' || attributeName === 'v-on:click') {
            return eNode
          }
        }
      }
    } while (((eNode = eNode.parentNode) !== null && eNode.nodeName !== '#document'))

    return null
  }

  _getParentId (target) {
    const id = target.id

    if (id) {
      return id
    }

    if (target.parentElement) {
      return this._getParentId(target.parentElement)
    }

    return null
  }

  _getLabel (target, attributes) {
    if (target.innerText) {
      return target.innerText.replace(/[\n\r]/, '')
    } else if (attributes['s_objectid']) {
      return attributes['s_objectid'].value
    } else if (attributes['aria-label']) {
      return attributes['aria-label'].value
    } else if (attributes['alt']) {
      return attributes['alt'].value
    } else if (attributes['title']) {
      return attributes['title'].value
    } else if (attributes['href']) {
      return attributes['href'].value
    } else if (attributes['src']) {
      return attributes['src'].value
    }

    if (target.parentElement) {
      return this._getLabel(target.parentElement, target.parentElement.attributes)
    }

    return null
  }

  init (endpoint, options = {}) {
    if (options.disabled) {
      // stop execution
      return
    }

    this.preview = false
    this.endpoint = endpoint
    this.viewUUID = uuidV4()
    this.url = window.document.URL
    this.prevState = null
    this.prevTime = null
    this.state = null
    this.name = options.name || options.tid || ''
    this.org = options.org || options.organization || ''
    this.uid = null

    this.webCollector = new WebCollector(this.name)
    this.webCollector.endpoint = endpoint
    this.webCollector.useQueryString = true
    this.webCollector.useBeacon = true

    const parsedUrl = url.parse(this.url, true)
    if (parsedUrl.query._op === '1') {
      console.log('OTM Preview MODE')
      this.preview = true

      if (parsedUrl.query._op_id) {
        const element = document.getElementById(parsedUrl.query._op_id)
        if (element) {
          element.style.border = '3px red solid'
        }
      } else if (parsedUrl.query._op_xpath) {
        const element = document.evaluate(parsedUrl.query._op_xpath, document).iterateNext()
        if (element) {
          element.style.border = '3px red solid'
        }
      }
    }

    let ref = null
    let st = Cookies.get('_st')
    if (document.referrer) {
      if (document.referrer === document.URL) {
        ref = Cookies.get('_pu')
      } else {
        ref = document.referrer
        st = null
      }
    }
    this.prevUrl = ref
    this.state = st

    document.addEventListener('click', (e) => {
      const wTarget = this._getWidgetElement(e.target)
      const target = wTarget || e.target
      const tagName = target.tagName.toLowerCase()
      const attributes = target.attributes
      const parentId = this._getParentId(target)
      let label = this._getLabel(target, attributes)
      const params = {}

      if (label) {
        if (parentId) {
          params.el = `${parentId}/${label.slice(0, 100)}`
        } else {
          params.el = label.slice(0, 100)
        }
      }

      for (let attribute of attributes) {
        let attributeName = attribute.name.toLowerCase()
        params['o_a_' + attributeName] = attribute.value
      }
      params.o_tag = tagName
      params.o_xpath = this._getXpathByElementNode(target)

      let stateSuffix = ''
      if (wTarget) {
        stateSuffix += 'widget'
      } else {
        stateSuffix += 'trivial'
      }

      stateSuffix += '_' + tagName
      if (params.o_a_id) {
        stateSuffix += '_id=' + params.o_a_id
      } else {
        const shaObj = new JsSHA('SHA-1', 'TEXT')
        if (label) {
          shaObj.update(`${parentId}${label}`)
          stateSuffix += '_lhash=' + shaObj.getHash('HEX')
        } else {
          shaObj.update(this.url + '_' + params.o_xpath)
          stateSuffix += '_hash=' + shaObj.getHash('HEX')
        }
      }
      params.stateSuffix = stateSuffix
      params.o_e_x = e.pageX
      params.o_e_y = e.pageY
      const rect = target.getBoundingClientRect()
      params.o_e_rl = rect.left + window.pageXOffset
      params.o_e_rt = rect.top + window.pageYOffset
      params.o_e_rw = rect.width
      params.o_e_rh = rect.height

      this.notify('click', params)
    })

    document.addEventListener('touchstart', (e) => {
      const wTarget = this._getWidgetElement(e.target)
      const target = wTarget || e.target
      const tagName = target.tagName.toLowerCase()
      const attributes = target.attributes
      let label = this._getLabel(target, attributes)
      const parentId = this._getParentId(target)
      const params = {}
      if (label) {
        if (parentId) {
          params.el = `${parentId}/${label.slice(0, 100)}`
        } else {
          params.el = label.slice(0, 100)
        }
      }

      for (let attribute of attributes) {
        params['o_a_' + attribute.name] = attribute.value
      }
      params.o_tag = tagName
      params.o_xpath = this._getXpathByElementNode(target)
      let stateSuffix = tagName
      if (params.o_a_id) {
        stateSuffix = tagName + '_id=' + params.o_a_id
      } else {
        const shaObj = new JsSHA('SHA-1', 'TEXT')
        if (label) {
          shaObj.update(`${parentId}${label}`)
          stateSuffix += '_lhash=' + shaObj.getHash('HEX')
        } else {
          shaObj.update(this.url + '_' + params.o_xpath)
          stateSuffix += '_hash=' + shaObj.getHash('HEX')
        }
      }
      params.stateSuffix = stateSuffix
      params.o_e_x = e.touches[0].pageX
      params.o_e_y = e.touches[0].pageY

      this.notify('touchstart', params)
    })

    if (options.observers) {
      this.observers = options.observers
    }

    this.notify('init')

    if (options.triggers) {
      for (let trigger of options.triggers) {
        if (trigger.type === 'timer') {
          if (!trigger.options.second) {
            console.error('There is no timer configuration.')
            continue
          }

          window.setInterval(() => {
            this.notify(trigger.id, {statePrefix: 'timer'})
          }, trigger.options.second * 1000)
        } else if (trigger.type === 'scroll') {
          let interval = trigger.options.interval || 5
          let threshold = trigger.options.threshold || 10
          trigger.x = this._scrollLeft()
          trigger.y = this._scrollTop()
          window.setInterval(() => {
            const x = this._scrollLeft()
            const y = this._scrollTop()
            const d = Math.abs(x - trigger.x) > threshold || Math.abs(y - trigger.y) > threshold
            trigger.x = x
            trigger.y = y
            if (d) {
              this.notify(trigger.id, {o_e_x: trigger.x, o_e_y: trigger.y, statePrefix: 'scroll'})
            }
          }, interval * 1000)
        }
      }
    }

    // observer url change on SPA
    const changeUrl = () => {
      if (this.url !== window.document.URL) {
        this.url = window.document.URL
        this.notify('change-url', {stateSuffix: '_url=' + window.document.URL})
      }
    }

    window.addEventListener('hashchange', changeUrl)
    setInterval(changeUrl, 50)

    if (window.PerformanceObserver && window.performance) {
      const pageview = (entries) => {
        const params = {}
        for (let entry of entries) {
          let key = null
          if (entry.name === 'first-paint') {
            key = 'o_fp'
          } else if (entry.name === 'first-contentful-paint') {
            key = 'o_fcp'
          }

          if (key) {
            params[key] = Math.round(entry.startTime + entry.duration)
          }
        }
        if (params.o_fp) {
          params.plt = params.o_fp
        }
        this.notify('pageview', params)
      }

      const currentEntries = window.performance.getEntriesByType('paint')
      if (currentEntries.length > 0) {
        pageview(currentEntries)
      } else {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          pageview(entries)
        })

        observer.observe({entryTypes: ['paint']})
      }
    } else {
      this.notify('pageview')
    }

    const sendWebVital = (m) => {
      this.performance('pageview', m.name, Math.round(m.value))
    }
    getCLS(sendWebVital)
    getFID(sendWebVital)
    getLCP(sendWebVital)
  }

  loadScript (src, attributes = {}) {
    const script = document.createElement('script')
    script.src = src
    for (let name in attributes) {
      script.setAttribute(name, attributes[name])
    }
    document.body.appendChild(script)
  }

  setUid (uid) {
    this.uid = uid
  }

  unsetUid () {
    this.uid = null
  }
}

export default OTM

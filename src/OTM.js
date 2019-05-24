import 'fetch-ie8'
import Cookies from 'cookies-js'
import uuidV4 from 'uuid/v4'
import JsSHA from 'jssha'
import url from 'url'

const OTM_VERSION = 1

const uuid = () => {
  return uuidV4().replace(/-/g, '')
}

class OTM {
  constructor () {
    this.observers = []
  }

  addObserver (target, func) {
    this.observers.push({target: target, func: func})
  }

  notify (target, params = {}) {
    for (let observer of this.observers.filter(observer => observer.target === target)) {
      if (observer.options.tag && observer.options.tag !== params.o_tag) {
        // skip notify event, because there is tag criteria
        return
      }

      if (observer.isNotified && observer.once) {
        continue
      }

      switch (observer.type) {
        case 'html':
          const fragment = document.createRange().createContextualFragment(observer.options.script)
          let node = fragment.firstChild
          while (node) {
            document.body.appendChild(node)
            node = fragment.firstChild
          }
          break
        case 'collect':
          // manage state for collect
          this.prevState = this.state
          let newState = target
          if (params.statePrefix) {
            newState = params.statePrefix + '_' + newState
            delete params.statePrefix
          }
          if (params.stateSuffix) {
            newState += '_' + params.stateSuffix
            delete params.stateSuffix
          }
          this.state = newState
          Cookies.set('_st', newState, {expires: 20})

          for (let n in observer.collect) {
            params[n] = observer.collect[n]
          }
          if (this.org) {
            params['org'] = this.org
          }
          this.call(observer.name, target, params)

          this.prevUrl = this.url
          Cookies.set('_pu', window.document.URL, {expires: 20})

          break
        case 'script':
          if (typeof observer.options.script === 'function') {
            observer.options.script(params)
          } else {
            // eslint-disable-next-line no-eval
            const func = eval('(function(params){' + observer.options.script + '})')
            func(params)
          }
          break
        case 'load-script':
          this.loadScript(observer.options.src, {})
          break
      }

      observer.isNotified = true
    }
  }

  call (name, target, params = {}) {
    if (this.preview) {
      console.log('call', name, target, params)
      return
    }

    params.v = OTM_VERSION
    params.tid = this.name
    params.dl = document.URL
    params.dt = document.title
    params.de = document.charset
    params.sd = window.screen.colorDepth + '-bit'
    params.ul = navigator.language
    params.sr = window.screen.width + 'x' + window.screen.height
    params.vp = window.innerWidth + 'x' + window.innerHeight
    if (target === 'pageview') {
      params.t = 'pageview'
    } else {
      params.t = 'event'
    }
    params.cid = this.userUUID
    params.ec = target
    params.ea = name
    params.o_cts = (new Date()).getTime()
    params.o_pl = this.prevUrl
    params.o_psid = this.viewUUID
    params.o_ps = this.prevState
    params.o_s = this.state
    params.o_r = uuid()

    const esc = encodeURIComponent
    const query = Object.keys(params).map(k => `${esc(k)}=${esc(params[k])}`).join('&')

    const myRequest = new Request(`${this.endpoint}?${query}`)

    fetch(myRequest, {
      method: 'GET',
      mode: 'cors'
    })
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

  _isImportantClick (eNode) {
    const NODE_TYPE_ELEMENT_NODE = 1

    if (eNode instanceof Array) {
      eNode = eNode[0]
    }

    if (eNode.nodeType !== NODE_TYPE_ELEMENT_NODE) {
      return ''
    }

    do {
      if (!eNode) {
        return false
      }

      let nodeName = eNode.nodeName.toLowerCase()
      if (nodeName === 'a' || nodeName === 'button') {
        return true
      }

      if (eNode.attributes) {
        for (let attribute of eNode.attributes) {
          let attributeName = attribute.name.toLowerCase()
          if (attributeName === 'onclick' || attributeName === 'ng-click' || attributeName === '@click' || attributeName === 'v-on:click') {
            return true
          }
        }
      }
    } while (((eNode = eNode.parentNode) !== null && eNode.nodeName !== '#document'))

    return false
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
    this.preview = false
    this.endpoint = endpoint
    this.viewUUID = uuid()
    this.url = window.document.URL
    this.prevState = null
    this.state = null
    this.name = options.name || ''
    this.org = options.org || ''

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

    this.userUUID = Cookies.get('_kk')
    if (!this.userUUID) {
      this.userUUID = uuid()
      Cookies.set('_kk', this.userUUID, {expires: 60 * 60 * 24 * 365 * 2})
    }
    this.prevUrl = Cookies.get('_pu')
    this.state = Cookies.get('_st')

    document.addEventListener('click', (e) => {
      const target = e.target
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
      params.o_xpath = this._getXpathByElementNode(e.target)

      let stateSuffix = ''
      if (this._isImportantClick(e.target)) {
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
          shaObj.update(this.url + '_' + params.o_xpath + '_' + JSON.stringify(params))
          stateSuffix += '_hash=' + shaObj.getHash('HEX')
        }
      }
      params.stateSuffix = stateSuffix
      params.o_e_x = e.pageX
      params.o_e_y = e.pageY

      this.notify('click', params)
    })

    document.addEventListener('touchstart', (e) => {
      const tagName = e.target.tagName.toLowerCase()
      const attributes = e.target.attributes
      let label = this._getLabel(e.target, attributes)
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
      params.o_xpath = this._getXpathByElementNode(e.target)
      let stateSuffix = tagName
      if (params.o_a_id) {
        stateSuffix = tagName + '_id=' + params.o_a_id
      } else {
        const shaObj = new JsSHA('SHA-1', 'TEXT')
        if (label) {
          shaObj.update(`${parentId}${label}`)
          stateSuffix += '_lhash=' + shaObj.getHash('HEX')
        } else {
          shaObj.update(this.url + '_' + params.o_xpath + '_' + JSON.stringify(params))
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

    setInterval(() => {
      if (this.url !== window.document.URL) {
        this.url = window.document.URL
        this.notify('change-url', {stateSuffix: '_url=' + window.document.URL})
      }
    }, 1000)

    this.notify('pageview')
  }

  loadScript (src, attributes = {}) {
    const script = document.createElement('script')
    script.src = src
    for (let name in attributes) {
      script.setAttribute(name, attributes[name])
    }
    document.body.appendChild(script)
  }
}

export default OTM

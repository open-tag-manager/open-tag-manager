import OTM from './OTM'

window.otmLayer = window.otmLayer || []
const layer = window.otmLayer

window.OTM = new OTM()
const otm = window.OTM

const processLayer = (data) => {
  if (data && 'event' in data) {
    switch (data.event) {
      case 'otm.init':
        otm.init(data['collect'], data['config'])
        break
      case 'otm.setuid':
        otm.setUid(data['uid'])
        break
      case 'otm.unsetuid':
        otm.unsetUid()
        break
      default:
        otm.notify(data.event, data)
    }
  }
}

for (const data of layer) {
  processLayer(data)
}

Object.defineProperty(layer, 'push', {
  value () {
    let n = this.length
    let l = arguments.length
    for (let i = 0; i < l; i++, n++) {
      this[n] = arguments[i]
      processLayer(this[n])
    }

    return n
  }
})

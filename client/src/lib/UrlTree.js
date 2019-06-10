import _ from 'lodash'
import urlparse from 'url'
import {lookupPath} from './GraphUril'

export function getTree (urls, currentConfig = {}) {
  const tree = {
    path: '',
    exists: false,
    children: [],
    level: 0,
    id: '/'
  }

  for (let url of urls) {
    if (!url) {
      continue
    }

    if (url.toLowerCase() === 'undefined') {
      continue
    }

    url = lookupPath(currentConfig, urlparse.parse(url)) || url

    let paths = urlparse.parse(url).pathname.replace(/%7b/gi, '{').replace(/%7d/gi, '}').split('/')
    if (paths.length === 1 || (paths.length === 2 && paths[1] === '')) {
      tree.exists = true
      continue
    }

    if (paths[paths.length - 1] === '') {
      paths = _.initial(paths)
    }

    let current = tree

    const pId = []
    for (let i in paths) {
      if (i === '0') {
        continue
      }
      pId.push(paths[i])

      let c = _.find(current.children, (c) => {
        return c.path === paths[i]
      })
      if (!c) {
        const newChild = {
          path: paths[i],
          exists: false,
          children: [],
          level: parseInt(i),
          id: pId.join('/'),
          hide: false
        }
        current.children.push(newChild)
        c = newChild
      }
      current = c

      if (paths.length - 1 === parseInt(i)) {
        c.exists = true
        let sObj = currentConfig['/' + pId.join('/')]
        if (sObj) {
          if (sObj.otmHideNode) {
            c.hide = true
          }
        }
      }
    }
  }

  return tree
}

export function getPathSample (tree) {
  const result = []

  const checkChild = function (path, children) {
    for (let child of children) {
      if (child.exists) {
        result.push({path: path + child.path, hide: child.hide})
      }
      checkChild(path + child.path + '/', child.children)
    }
  }

  if (tree.exists) {
    result.push({path: '/'})
  }

  checkChild('/', tree.children)
  const swagger = {'paths': {}}
  for (let path of result.reverse()) {
    let o = {}
    if (path.hide) {
      o.otmHideNode = path.hide
    }
    swagger.paths[path.path] = o
  }

  return swagger
}

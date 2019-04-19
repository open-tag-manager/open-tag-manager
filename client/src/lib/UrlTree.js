import _ from 'lodash'
import urlparse from 'url'

export function getTree (urls) {
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

    let paths = urlparse.parse(url).pathname.split('/')
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
          id: pId.join('/')
        }
        current.children.push(newChild)
        c = newChild
      }
      current = c

      if (paths.length - 1 === parseInt(i)) {
        c.exists = true
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
        result.push(path + child.path)
      }
      checkChild(path + child.path + '/', child.children)
    }
  }

  if (tree.exists) {
    result.push('/')
  }

  checkChild('/', tree.children)
  const swagger = {'paths': {}}
  for (let path of result.reverse()) {
    swagger.paths[path] = {}
  }

  return swagger
}

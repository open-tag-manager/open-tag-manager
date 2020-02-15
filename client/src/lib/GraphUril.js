import _ from 'lodash'
import url from 'url'
import querystring from 'querystring'

export function getUrls (data) {
  const urls = []
  for (let d of data) {
    if (d.url && !_.includes(urls, d.url)) {
      urls.push(d.url)
    }
    if (d.p_url && !_.includes(urls, d.p_url)) {
      urls.push(d.p_url)
    }
  }
  return urls
}

export function filterByUrl (data, url) {
  const newData = _.filter(data, {url})

  _.each(data, (d) => {
    if (d.url === url) {
      return
    }

    if (d.p_url === url) {
      newData.push(d)
    }
  })

  return newData
}

export function mergeSameId (data) {
  const cData = []

  for (let d of data) {
    if (d.deleted) {
      continue
    }

    const filtered = _.filter(data, {url: d.url, p_url: d.p_url, state: d.state, p_state: d.p_state})
    if (filtered.length <= 1) {
      cData.push(d)
    } else {
      let count = 0
      for (let fd of filtered) {
        count += fd.count
        fd.deleted = true
      }

      delete d.deleted
      d.count = count
      cData.push(d)
    }
  }

  return cData
}

export const lookupPath = function (paths, parsedUrl) {
  if (!parsedUrl.path) {
    return null
  }

  let path = parsedUrl.path
  if (parsedUrl.hash) {
    const match = parsedUrl.hash.match(/^#!(\/.*)/)
    if (match) {
      const hashUrl = url.parse(match[1])
      path = hashUrl.path
    }
  }

  let m = path.match(/^(.*)\/$/)
  if (m) {
    path = m[1]
  }

  const targetUrl = url.parse(path)
  const targetQs = querystring.parse(targetUrl.query)

  for (let p in paths) {
    const u = url.parse(p)
    const r = new RegExp('^' + u.pathname.replace(/{[^}]*}/g, '[^/]*') + '$')
    if (r.exec(targetUrl.pathname)) {
      // match pathname
      if (u.query) {
        let queryMatch = true
        const qs = querystring.parse(u.query)
        for (let qd in qs) {
          const qr = new RegExp('^' + qs[qd].replace(/{[^}]*}/g, '[^/]*') + '$')
          if (!qr.exec(targetQs[qd])) {
            queryMatch = false
            break
          }
        }
        if (queryMatch) {
          return `${parsedUrl.protocol}//${parsedUrl.host}${p}`
        }
      } else {
        return `${parsedUrl.protocol}//${parsedUrl.host}${p}`
      }
    }
  }

  return null
}

export function convertUrlForTableData (data, swaggerDoc) {
  const cData = _.cloneDeep(data)
  if (!swaggerDoc) {
    return data
  }

  const paths = JSON.parse(swaggerDoc).paths

  if (!paths) {
    return data
  }
  for (let d of cData) {
    let newUrl = lookupPath(paths, url.parse(d.url)) || d.url
    if (d.url === newUrl) {
      continue
    }
    d.url = newUrl
  }

  return cData
}

export function convertUrl (data, swaggerDoc) {
  if (!swaggerDoc) {
    return data
  }

  const paths = JSON.parse(swaggerDoc).paths

  if (!paths) {
    return data
  }

  for (let d of data) {
    let newUrl = lookupPath(paths, url.parse(d.url)) || d.url
    let newPUrl = d.p_url ? lookupPath(paths, url.parse(d.p_url)) || d.p_url : null

    // remove duplicated record
    const e = _.find(data, {url: newUrl, p_url: newPUrl, state: d.state, p_state: d.p_state, m: true})
    if (e) {
      e.count += d.count
      d.url = null
    } else {
      d.url = newUrl
      d.p_url = newPUrl
      d.m = true
    }
  }

  return _.reject(data, (d) => {
    return d.url === null
  })
}

const findRelatedEdge = function (data, edges, skipStatePatterns, results = [], path = []) {
  for (let e of edges) {
    if (e['p_state'] === e['state']) {
      continue
    }
    let idx = _.findIndex(skipStatePatterns, (p) => {
      return e['p_state'] && e['p_state'].match(p)
    })
    if (idx === -1) {
      results.push(e)
    } else {
      // prevent circular reference
      let si = _.findIndex(path, (pe) => {
        return pe['p_state'] && pe['p_state'] === e['p_state']
      })
      if (si !== -1) {
        continue
      }

      let searchCondition = {}
      searchCondition['state'] = e['p_state']
      searchCondition.url = e.p_url
      let deepEdges = _.filter(data, searchCondition)
      path.push(e)
      findRelatedEdge(data, deepEdges, skipStatePatterns, results, path)
    }
  }

  return results
}

export function skipData (data, skipStatePatterns = [], thresholdCount) {
  const cData = _.cloneDeep(data)
  // Mark as skip
  for (let d of cData) {
    let sourceMatched = false
    let targetMatched = false
    for (let pattern of skipStatePatterns) {
      if (d['p_state'] && d['p_state'].match(pattern)) sourceMatched = true
      if (d['state'] && d['state'].match(pattern)) targetMatched = true
    }
    if (d['count'] < thresholdCount) targetMatched = true
    d.sourceSkip = sourceMatched
    d.targetSkip = targetMatched
  }

  // Modify edge
  for (let d of cData) {
    if (d.targetSkip) {
      continue
    }
    if (d.sourceSkip) {
      let searchCondition = {}
      searchCondition['state'] = d['p_state']
      searchCondition.url = d.p_url
      let edges = _.filter(data, searchCondition)
      edges = findRelatedEdge(data, edges, skipStatePatterns)
      for (let e of edges) {
        let searchCondition2 = {}
        searchCondition2['p_state'] = e['p_state']
        searchCondition2['state'] = d['state']
        let existsEdge = _.find(cData, searchCondition2)
        let count = e['count'] > d['count'] ? d['count'] : e['count']
        if (existsEdge) {
          existsEdge['count'] += count
        } else {
          let newEdge = {}
          newEdge['p_state'] = e['p_state']
          newEdge['state'] = d['state']
          newEdge.url = d.url
          newEdge.p_url = d.p_url
          newEdge.title = d.title
          newEdge.label = d.label
          newEdge.xpath = d.xpath
          newEdge.a_id = d.a_id
          newEdge.class = d.class
          newEdge['count'] = count
          cData.push(newEdge)
        }
      }
    }
  }

  // Delete skipped edge
  return _.reject(_.reject(cData, 'sourceSkip'), 'targetSkip')
}

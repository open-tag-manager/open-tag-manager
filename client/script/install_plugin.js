const camelize = require('camelize')
const glob = require('glob')
const fs = require('fs')
const { execSync } = require('child_process')

const plugins = []
const lines1 = []
const lines2 = []
glob('../plugins/*/client/', (err, files) => {
  for (var i in files) {
    try {
      const packageFile = `${files[i]}package.json`
      fs.accessSync(packageFile, fs.constants.R_OK)
      execSync('yarn link', {cwd: files[i]})
      const packageData = require(`../${packageFile}`)
      plugins.push(packageData.name)
      execSync(`yarn link ${packageData.name}`)
    } catch (err) {
    }
  }

  for (var i in plugins) {
    const camelizedPluginName = camelize(plugins[i])
    lines1.push(`import ${camelizedPluginName} from '${plugins[i]}'`)
    lines2.push(`plugins.push(${camelizedPluginName}())`)
  }
  lines1.push('const plugins = []')
  lines2.push('export default plugins')
  fs.writeFileSync('src/plugins.js', lines1.concat(lines2).join('\n'))
})

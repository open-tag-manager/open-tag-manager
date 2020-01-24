import glob
import os
import json
import shutil

def main():
    dir = os.path.dirname(os.path.abspath(__file__))
    plugin_dir = dir + '/chalicelib/otmplugins'
    shutil.rmtree(plugin_dir, ignore_errors=True)
    os.mkdir(plugin_dir)
    apis = []
    for file in glob.iglob(dir + '/../plugins/*/package.json'):
        with open(file) as f:
            data = json.load(f)
            if 'otm' not in data:
                continue
            if 'apis' not in data['otm']:
                continue

            # copy modules
            shutil.copytree(os.path.dirname(file) + '/client_apis', plugin_dir + '/' + data['name'])

            for api in data['otm']['apis']:
                api['package'] = data['name']
                apis.append(api)

    with open(dir + '/.chalice/config.json', 'r') as f:
        config = json.load(f)
        env = config['environment_variables']
        env['OTM_PLUGINS'] = json.dumps(apis)

    with open(dir + '/.chalice/config.json', 'w') as f:
        json.dump(config, f, indent=4)


if __name__ == '__main__':
    main()

import glob
import os
import json
import shutil
import argparse


def main():
    parser = argparse.ArgumentParser(description='install_plugin for OTM client APIs')
    parser.add_argument('--dev', dest='dev', help='local development mode', action='store_true')
    args = parser.parse_args()

    requirements = []
    base_dir = os.path.dirname(os.path.abspath(__file__))

    with open(base_dir + '/requirements_base.txt', 'r') as f:
        requirements.append(f.read())

    plugin_dir = base_dir + '/chalicelib/otmplugins'
    shutil.rmtree(plugin_dir, ignore_errors=True)
    os.mkdir(plugin_dir)
    apis = []
    for file in glob.iglob(base_dir + '/../plugins/*/package.json'):
        print(file)
        with open(file) as f:
            data = json.load(f)
            if 'otm' not in data:
                continue
            if 'apis' not in data['otm']:
                continue

            # copy modules
            if args.dev:
                # development mode (create symlink)
                os.symlink(os.path.dirname(file) + '/client_apis', plugin_dir + '/' + data['name'])
            else:
                # production mode
                shutil.copytree(os.path.dirname(file) + '/client_apis', plugin_dir + '/' + data['name'])

            if os.path.exists(os.path.dirname(file) + '/client_apis/requirements.txt'):
                with open(os.path.dirname(file) + '/client_apis/requirements.txt', 'r') as rf:
                    requirements.append(rf.read())

            for api in data['otm']['apis']:
                api['package'] = data['name']
                apis.append(api)

    with open(base_dir + '/.chalice/config.json', 'r') as f:
        config = json.load(f)
        env = config['environment_variables']
        env['OTM_PLUGINS'] = json.dumps(apis)

    with open(base_dir + '/.chalice/config.json', 'w') as f:
        json.dump(config, f, indent=4)

    with open(base_dir + '/requirements.txt', 'w') as f:
        f.writelines(requirements)


if __name__ == '__main__':
    main()

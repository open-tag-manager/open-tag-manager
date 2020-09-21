import glob
import os
import json
import shutil
import argparse


def main():
    parser = argparse.ArgumentParser(description='install_plugin for OTM data_retriever')
    parser.add_argument('--dev', dest='dev', help='local development mode', action='store_true')
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_dir = base_dir + '/otmplugins'
    shutil.rmtree(plugin_dir, ignore_errors=True)
    os.mkdir(plugin_dir)
    for file in glob.iglob(base_dir + '/../plugins/*/package.json'):
        with open(file) as f:
            data = json.load(f)

        if os.path.exists(os.path.dirname(file) + '/data_retriever'):
            if args.dev:
                os.symlink(os.path.dirname(file) + '/data_retriever', plugin_dir + '/' + data['name'])
            else:
                shutil.copytree(os.path.dirname(file) + '/data_retriever', plugin_dir + '/' + data['name'])


if __name__ == '__main__':
    main()

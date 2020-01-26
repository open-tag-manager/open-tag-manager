import glob
import os
import json
import shutil


def main():
    dir = os.path.dirname(os.path.abspath(__file__))
    plugin_dir = dir + '/otmplugins'
    shutil.rmtree(plugin_dir, ignore_errors=True)
    os.mkdir(plugin_dir)
    for file in glob.iglob(dir + '/../plugins/*/package.json'):
        with open(file) as f:
            data = json.load(f)

        if os.path.exists(os.path.dirname(file) + '/data_retriever'):
            shutil.copytree(os.path.dirname(file) + '/data_retriever', plugin_dir + '/' + data['name'])


if __name__ == '__main__':
    main()

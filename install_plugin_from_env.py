import subprocess
import os

def main():
    plugins = (os.environ.get('OTM_PLUGINS') or '')
    if plugins:
        for plugin_url in plugins.split(' '):
            subprocess.run(['git', 'clone', plugin_url], cwd='./plugins', check=False)

if __name__ == '__main__':
    main()

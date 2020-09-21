import subprocess
import os


def main():
    plugins = (os.environ.get('OTM_PLUGINS') or '')
    if plugins:
        for plugin in plugins.split(' '):
            plugin_info = plugin.split('=')
            command = ['git', 'clone', plugin_info[0]]
            if len(plugin_info) > 1:
                command.append('-b')
                command.append(plugin_info[1])
                command.append('--depth')
                command.append('1')
            subprocess.run(command, cwd='./plugins', check=False)


if __name__ == '__main__':
    main()

import json
import argparse
from decimal import Decimal


def decimal_default_proc(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class ScriptGenerator:
    def __init__(self, src_url, collect_url):
        self._src_url = src_url
        self._collect_url = collect_url
        self._config = {}

    def load_config_file(self, path):
        self._config = json.load(open(path, 'r'))

    def import_config(self, config):
        self._config = config

    def generate(self):
        return '''(function() {
var script = document.createElement('script');
script.src = "%s";
script.onload = function() {
  OTM.init("%s", %s)
}
if (document.readyState === 'loading') {
  window.addEventListener('DOMContentLoaded', function() {
    document.body.appendChild(script);
  });
} else {
  document.body.appendChild(script);
}
})()
''' % (self._src_url, self._collect_url, json.dumps(self._config, ensure_ascii=False, default=decimal_default_proc))


def main():
    parser = argparse.ArgumentParser(description='Generate script')
    parser.add_argument('-s', '--src', dest='src', required=True, help='src URL for Open Tag Manager')
    parser.add_argument('-p', '--collect', dest='collect', required=True, help='collect URL for Open Tag Manager')
    parser.add_argument('-c', '--config', dest='config', required=True, help='config file path')
    parser.add_argument('-o', '--output', dest='output', required=True, help='output path')
    args = parser.parse_args()

    scriptGenerator = ScriptGenerator(args.src, args.collect)
    scriptGenerator.load_config_file(args.config)
    script = scriptGenerator.generate()

    if args.output == '-':
        print(script)
    else:
        f = open(args.output, 'w')
        f.write(script)
        f.close()

        print("You can upload script by following:\n")
        print('python scripts/upload.py -p COLLECT_BUCKET -b SCRIPT_BUCKET -s %s -n NAME' % args.output)


if __name__ == '__main__':
    main()

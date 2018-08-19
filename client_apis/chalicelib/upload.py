import os
import boto3
import argparse


class S3Uploader:
    def __init__(self, collect_bucket, script_bucket, otm_path):
        self._s3 = boto3.resource('s3')
        self._collect_bucket = collect_bucket
        self._script_bucket = script_bucket
        self._otm_path = otm_path
        self._script_name = None
        if collect_bucket:
            self._collect_location = boto3.client('s3').get_bucket_location(Bucket=collect_bucket)['LocationConstraint']
        self._script_location = boto3.client('s3').get_bucket_location(Bucket=script_bucket)['LocationConstraint']

    def upload_general(self):
        self._s3.Object(self._collect_bucket, 'collect.html').put(Body='', ACL='public-read', ContentType='text/html',
                                                            Metadata={'Cache-Control': 'public, max-age=315360000'})
        self._s3.Object(self._script_bucket, 'otm.js').put(Body=open(self._otm_path, 'rb'),
                                                           ACL='public-read',
                                                           ContentType='text/javascript',
                                                           Metadata={'Cache-Control': 'public, max-age=1800'})

    def upload_script_by_file(self, name, script_path):
        self._s3.Object(self._script_bucket, name).put(Body=open(script_path, 'rb'), ACL='public-read',
                                                       ContentType='text/javascript',
                                                       Metadata={'Cache-Control': 'public, max-age=1800'})
        self._script_name = name

    def upload_script(self, name, body):
        self._s3.Object(self._script_bucket, name).put(Body=body, ACL='public-read',
                                                       ContentType='text/javascript',
                                                       Metadata={'Cache-Control': 'public, max-age=1800'})
        self._script_name = name

    def collect_url(self):
        return 'https://s3-%s.amazonaws.com/%s/collect.html' % (
            self._collect_location,
            self._collect_bucket)

    def otm_url(self):
        return 'https://s3-%s.amazonaws.com/%s/otm.js' % (
            self._script_location,
            self._script_bucket)

    def script_url(self):
        return 'https://s3-%s.amazonaws.com/%s/%s' % (
            self._script_location,
            self._script_bucket,
            self._script_name)


def main():
    parser = argparse.ArgumentParser(description='Upload scripts to S3')
    parser.add_argument('-p', '--collect-bucket', dest='collect', required=True, help='collect bucket')
    parser.add_argument('-b', '--script-bucket', dest='s_bucket', required=True, help='Script bucket')
    parser.add_argument('-s', '--script-src', dest='s_src', help='Script src file path')
    parser.add_argument('-n', '--script-name', dest='s_name', help='Script name in bucket')
    args = parser.parse_args()

    uploader = S3Uploader(args.collect, args.s_bucket, os.path.dirname(__file__) + '/../../dist/otm.js')
    uploader.upload_general()
    print('collect: %s' % uploader.collect_url())
    print('OTM: %s' % uploader.otm_url())

    if args.s_src and args.s_name:
        uploader.upload_script_by_file(args.s_name, args.s_src)
        print('SCRIPT: %s' % uploader.script_url())
        print("Embed script to your website:\n")
        print('<script src="%s"></script>' % (uploader.script_url()))
    else:
        print("You can generate script file by following:\n")
        print('python scripts/script_generator.py -p %s -s %s -c config.sample.json -o test.js' % (
            uploader.collect_url(), uploader.otm_url()))


if __name__ == '__main__':
    main()

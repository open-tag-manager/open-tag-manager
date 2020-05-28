from chalice import Chalice
from urllib import parse as urlparse
from datetime import datetime
import os
import json
import boto3
import gzip
import tempfile
import re

app = Chalice(app_name='otm_log_formatter')
s3 = boto3.resource('s3')


def read_cf_data(bucket_name, object_key):
    obj = s3.Object(bucket_name, object_key)
    with tempfile.TemporaryFile() as temp:
        obj.download_fileobj(temp)
        temp.seek(0)
        with gzip.GzipFile(fileobj=temp) as gz:
            for b in gz:
                yield b


@app.on_sns_message(topic=os.environ.get('OTM_LOG_SNS'))
def handler(event):
    records = json.loads(event.message)
    record = records['Records'][0]
    if record['eventName'] != 'ObjectCreated:Put':
        return None

    bucket_name = record['s3']['bucket']['name']
    object_key = record['s3']['object']['key']

    comment_pattern = re.compile('^#')

    file_name = re.compile('(.*/)?(.+)$').match(object_key)[2]

    result = {}
    record_count = {}
    for b in read_cf_data(bucket_name, object_key):
        str = b.decode('utf-8')
        if comment_pattern.match(str):
            continue
        data = str.rstrip().split('\t')
        record_data = {
            'x_edge_location': data[2],
            'sc_bytes': data[3],
            'c_ip': data[4],
            'cs_method': data[5],
            'cs_host': data[6],
            'cs_uri_stem': data[7],
            'cs_status': data[8],
            'cs_referer': data[9],
            'cs_user_agent': data[10],
            'cs_uri_query': data[11],
            'cs_cookie': data[12],
            'cs_x_edge_result_type': data[13],
            'cs_x_edge_request_id': data[14],
            'x_host_header': data[15],
            'cs_protocol': data[16],
            'cs_bytes': data[17],
            'time_taken': data[18],
            'x_forwarded_for': data[19],
            'ssl_protocol': data[20],
            'ssl_cipher': data[21],
            'x_edge_response_result_type': data[22],
            'cs_protocol_version': data[23],
            'fle_status': data[24],
            'fle_encrypted_fields': data[25]
        }
        url_query = urlparse.parse_qs(urlparse.unquote(record_data['cs_uri_query']))
        qs_json = {}
        for key in url_query:
            qs_json[key] = url_query[key][0]

        record_data['qs'] = qs_json

        tid = 'null'
        if 'tid' in qs_json:
            tid = qs_json['tid']

        org = 'root'
        if 'org' in qs_json:
            org = qs_json['org']

        ts = datetime.strptime(data[0] + ' ' + data[1], '%Y-%m-%d %H:%M:%S')
        record_data['datetime'] = ts.strftime('%Y-%m-%d %H:%M:%S')
        prefix = "org=%s/tid=%s/%s" % (org, tid, ts.strftime('year=%Y/month=%-m/day=%-d'))
        new_key = "%s/%s" % (prefix, file_name)

        if new_key not in result:
            result[new_key] = []

        if new_key not in record_count:
            record_count[new_key] = 0

        result[new_key].append(json.dumps(record_data))
        record_count[new_key] += 1

    for key in result:
        obj = s3.Object(os.environ.get('OTM_REFORM_S3_BUCKET'), os.environ.get('OTM_REFORM_LOG_PREFIX') + key)
        obj.put(Body=gzip.compress('\n'.join(result[key]).encode('utf-8')))

    for key in record_count:
        file_name = os.path.splitext(key)[0]
        obj = s3.Object(os.environ.get('OTM_STAT_S3_BUCKET'), os.environ.get('OTM_STAT_LOG_PREFIX') + file_name + '.json')
        obj.put(Body=json.dumps({'type': 'collect', 'size': record_count[key]}))

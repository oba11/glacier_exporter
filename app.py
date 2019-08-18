from collections import Counter
import sys
import time
import os
import logging
import boto3
import yaml
from prometheus_client import start_http_server, Metric, REGISTRY
from util import memoize

# Logging config
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
log.setLevel(logging.INFO)

if os.getenv('DEBUG', 'false').lower() == 'true':
    logging.basicConfig(level=logging.DEBUG)
    log.setLevel(logging.DEBUG)


class GlacierGauge:
    def collect(self):
        config = self.read_config()
        for bucket in config['buckets']:
            stat = self.s3_glacier_stat(bucket, config['region'], config.get('role_arn', None))
            log.debug(stat)
            for x, y in stat.items():
                metric = Metric(x, x, 'gauge')
                if isinstance(y, dict):
                    for storage_type, value in y.items():
                        metric.add_sample(x,
                                          value=value,
                                          labels={
                                              'bucket_name': bucket,
                                              'storage_type': storage_type
                                          })
                    if metric.samples:
                        yield metric
                    else:
                        pass
                else:
                    metric.add_sample(x, value=y, labels={'bucket_name': bucket})
                    if metric.samples:
                        yield metric
                    else:
                        pass

    def read_config(self):
        # pylint: disable=R0201
        configfile = os.path.join(os.path.dirname(__file__), 'config.yml')
        if os.getenv('CONFIG_PATH'):
            configfile = os.getenv('CONFIG_PATH')
            log.info(os.path.exists(configfile))
            log.debug(configfile)
        if not (os.path.exists(configfile) and os.stat(configfile).st_size > 0):
            log.error('cannot read config file: {}'.format(configfile))
            sys.exit(1)
        return yaml.safe_load(open(configfile))

    @memoize(expiry_time=12 * 60 * 60)
    def s3_glacier_stat(self, bucket, region, role_arn=None):
        result = {}
        result['aws_s3_number_of_objects_count'] = Counter()
        result['aws_s3_objects_size_bytes'] = Counter()
        start_time = time.time()
        kwargs = {'Bucket': bucket, 'MaxKeys': 1000}

        if role_arn:
            client = self.session(role_arn=role_arn).client('s3', region_name=region)
        else:
            log.info('Using client credentials')
            client = boto3.client('s3', region_name=region)

        log.info('Starting to query the s3 bucket:{}'.format(bucket))
        while True:
            resp = client.list_objects_v2(**kwargs)
            contents = resp['Contents'] if 'Contents' in resp else []
            for obj in contents:
                result['aws_s3_number_of_objects_count'][obj['StorageClass']] += 1
                result['aws_s3_objects_size_bytes'][obj['StorageClass']] += obj['Size']
            if resp.get('NextContinuationToken'):
                kwargs['ContinuationToken'] = resp['NextContinuationToken']
            else:
                log.info('Completed the querying of the s3 bucket')
                break
        result.update({'request_processing_duration': (time.time() - start_time)})
        return result

    @memoize(expiry_time=45 * 60)
    def session(self, role_arn):
        # pylint: disable=R0201
        log.info('Retrieving session for assumed role')
        sts = boto3.client('sts')
        user = sts.get_caller_identity()['Arn'].split('/')[-1]
        resp = sts.assume_role(RoleArn=role_arn, RoleSessionName=user)
        return boto3.Session(aws_access_key_id=resp['Credentials']['AccessKeyId'],
                             aws_secret_access_key=resp['Credentials']['SecretAccessKey'],
                             aws_session_token=resp['Credentials']['SessionToken'])


if __name__ == '__main__':
    start_http_server(9109)
    log.info('Starting s3-exporter on port :9109')
    REGISTRY.register(GlacierGauge())
    while True:
        time.sleep(5)

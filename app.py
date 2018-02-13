from util import memoize
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY
import time
import boto3
import yaml,os
import logging,sys

# Logging config
loglevel = logging.INFO
if os.getenv('DEBUG', 'false').lower() == 'true':
	loglevel = logging.DEBUG
log = logging.getLogger(__name__)
log.setLevel(loglevel)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(loglevel)
formatter = logging.Formatter('%(asctime)s - %(levelname)s == %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)

class GlacierGauge(object):
	def collect(self):
		config = self.read_config()
		for bucket in config['buckets']:	
			stat = self.s3_glacier_stat(bucket,config['region'],config.get('role_arn',None))
			for x,y in stat.items():
				metric = GaugeMetricFamily(x, x, labels=["bucket_name"])
				metric.add_metric([bucket], y)
				yield metric

	def read_config(self):
		configfile = os.path.join(os.path.dirname(__file__), 'config.yaml')
		if os.getenv('CONFIG_PATH'):
			configfile = os.getenv('CONFIG_PATH')
			print(os.path.exists(configfile))
		if not (os.path.exists(configfile) and os.stat(configfile).st_size > 0):
			log.error('cannot read config file: {}'.format(configfile))
			sys.exit(1)
		return yaml.safe_load(open(configfile))

	@memoize(expiry_time=12*60*60)
	def s3_glacier_stat(self, bucket, region, role_arn=None):
		count = 0
		size = 0
		result = {}
		start_time = time.time()
		kwargs = {'Bucket': bucket, 'MaxKeys': 1000}

		if role_arn:
			s3 = self.session(role_arn=role_arn).client('s3',region_name=region)
		else:
			s3 = boto3.client('s3',region_name=region)

		log.info('Starting to query the s3 bucket')
		while True:
			resp = s3.list_objects_v2(**kwargs)
			for obj in resp['Contents']:
				if obj['StorageClass'] == 'GLACIER':
					size += obj['Size']
					count += 1
			if resp.get('NextContinuationToken'):
				kwargs['ContinuationToken'] = resp['NextContinuationToken']
			else:
				log.info('Completed the querying of the s3 bucket')
				break
		result.update({
			'aws_s3_number_of_glacier_objects': count,
			'aws_s3_glacier_objects_size_bytes': size,
			'request_processing_duration': (time.time() - start_time)
		})
		return result

	@memoize(expiry_time=45*60)
	def session(self, role_arn):
		log.info('Retrieving session for assumed role')
		sts = boto3.client('sts')
		user = sts.get_caller_identity()['Arn'].split('/')[-1]
		resp = sts.assume_role(
			RoleArn=role_arn,
			RoleSessionName=user
		)
		return boto3.Session(
			aws_access_key_id=resp['Credentials']['AccessKeyId'],
			aws_secret_access_key=resp['Credentials']['SecretAccessKey'],
			aws_session_token=resp['Credentials']['SessionToken'])

if __name__ == '__main__':
	start_http_server(9109)
	while True:
		REGISTRY.register(GlacierGauge())
		time.sleep(3600)

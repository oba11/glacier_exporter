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
			stat = self.s3_glacier_stat(bucket,config['region'])
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
	def s3_glacier_stat(self, bucket, region):
		count = 0
		size = 0
		result = {}
		start_time = time.time()
		log.info('Starting to query the s3 bucket')
		kwargs = {'Bucket': bucket, 'MaxKeys': 1000}
		s3 = boto3.client('s3',region_name=region)
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

if __name__ == '__main__':
	start_http_server(9109)
	while True:
		REGISTRY.register(GlacierGauge())
		time.sleep(3600)

# Glacier exporter

Prometheus exporter for glacier metrics. This exporter is useful to retrieve the number of archives in the vault and the size of the vault.

## Building and running

### Docker

```
docker run -d -p 9109:9109 -v config.yml:/src/config.yml oba11/glacier-exporter

OR

docker run -d -p 9109:9109 -v config.yml:/config/config.yml -e CONFIG_PATH=/config/config.yml oba11/glacier-exporter
```

## Configuration

The configuration is in YAML, an example with common options:

```
---
region: eu-west-1
buckets:
	- bucket_one
	- bucket_two
```

IAM Policy

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

Name | Description
-----|------------
region   | Required. The AWS region to connect to.
role_arn   | Optional. The AWS role to assume. Useful for retrieving cross account metrics.
buckets  | Required. A list of s3 buckets to retrieve and export metrics

## Metrics

List of metrics exposed by the exporter

Name | Description | Type
--------|------------|------------
`aws_s3_number_of_glacier_objects`   |  The number of objects in glacier storage | gauge 
`aws_s3_glacier_objects_size_bytes`   |  The size of objects in glacier storage | gauge 
`request_processing_duration`   |  How long it took to retrieve all the data for the bucket | gauge 

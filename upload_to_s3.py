import boto3
from boto3.s3.transfer import TransferConfig

def uploadFileS3(filename='hello.txt', s3_bucket='some-bucket', file_path='/home/users/file', key_path='/', aws_access_key_id = 'AAAA', aws_secret_key='BBBB', region='us-west-1'):
    s3 = boto3.resource('s3',region_name=region,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_key)
    config = TransferConfig(multipart_threshold=1024*25, max_concurrency=10,
                        multipart_chunksize=1024*25, use_threads=True)
    file = file_path + '/' + filename
    data = open(file, 'rb')
    s3.Bucket(s3_bucket).put_object(Key=filename, Body=data)

uploadFileS3()

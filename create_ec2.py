import boto3, time, logging

def create_ec2():
    boto3.set_stream_logger('boto3', logging.DEBUG)
    ec2 = boto3.resource('ec2')
    instance = ec2.create_instances(
        ImageId = 'ami-id',
        MinCount = 1,
        MaxCount = 1,
        InstanceType = 't2.micro',
        KeyName = 'common_dev_key',
        SubnetId = 'subnet-id')[0]
    print ('Created Instance: ', instance.id)
    instance.wait_until_running()
    time.sleep(5)

    ec2_client=boto3.client('ec2')
    waiter = ec2_client.get_waiter('instance_running')
    print (waiter.wait(InstanceIds=[instance.id]))
    print instance.state
    while instance.state['Name'] != 'running':
       print('Instance is in %s state, sleeping 10 secs',instance.state['Name']))
       time.sleep(10)
       instance.load()

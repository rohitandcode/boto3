import boto3
import json
from datetime import timedelta

def get_pricing(region, resource, access_key=None, secret_key=None):
    """Returns up-to-date pricing of EC2 instances and volumes from
       AWS Price List Service (Pricing)

    Args: region (str): AWS Region
          resource (str): AWS resource type ex: r4.16xlarge,i3.4xlarge,
                          gp2 or io1 volumetype
          access_key (str): AWS access key ID
          secret_key (str): AWS secret key
    Returns: (float) costs
    """
    # Here us-east-1 is the pricing endpoint to fetch the prices
    cost_client = boto3.client('pricing', region_name='us-east-1',
                               aws_access_key_id=access_key,
                               aws_secret_access_key=secret_key)

    # cost_client takes region value in a human readable form,
    # fetching region name from constants

    region_value = AWSConstants.AWS_REGIONS_DICT.get(region)
    if region_value is None:
        raise ValueError('Region "{}" is not supported.'.format(region))

    # function to return the filter_type based on field, value
    def _filter_list(field_list, value_list):
        flist = [{'Type': 'TERM_MATCH', 'Field': f, 'Value': v}
                  for f, v in zip(field_list, value_list)]
        return flist

    # Mapping short-region name to long
    if resource == 'io1':
        service_code = 'AmazonEC2'
        filter_type = _filter_list(['volumeType', 'location'],
                                   ['Provisioned IOPS', region_value])
    elif resource == 'gp2':
        service_code = 'AmazonEC2'
        filter_type = _filter_list(['volumeType', 'location'],
                                   ['General Purpose', region_value])
    elif resource == 's3':
        service_code = 'AmazonS3'
        filter_type = _filter_list(['productFamily', 'usagetype'],
                                   ['Storage', 'USW2-TimedStorage-ByteHrs'])
    else:  # Assuming resource is a EC2 instance
        service_code = 'AmazonEC2'
        filter_type = _filter_list(['operatingSystem', 'location',
                                    'instanceType', 'tenancy',
                                    'preInstalledSw'],
                                   ['Linux', region_value, resource,
                                    'Shared', 'NA'])

    # Parsing price
    response = cost_client.get_products(
        ServiceCode=service_code,
        Filters=filter_type)
    unit_price = 0
    for price_list in response['PriceList']:
        price_item = json.loads(price_list)
        for price_terms in price_item['terms']['OnDemand'].values():
            for price_dimensions in price_terms['priceDimensions'].values():
                for unit in price_dimensions['pricePerUnit'].values():
                    unit_price = unit
    return float(unit_price)

def get_ec2_costs(ec2_instances, region, total_test_time, access_key=None,
                  secret_key=None):
    """Calculates and returns total cost of all
       EC2 instances - Controller and VD instances

    Args: ec2_instances (list): List containing information of all the instances
                                Obtained from aws_discovery.ResourcesDiscovery
          region (str): AWS Region
          total_test_time (int): (secs) Total time of test run in Jenkins
          access_key (str): AWS access key ID
          secret_key (str): AWS secret key
    Returns: costs
    """
    ec2 = [i.description['Reservations'][0]['Instances'][0]['InstanceType']
           for i in ec2_instances]
    if not ec2:
        th.info("No EC2 instances found! returning costs as $0.")
        return 0
    # Calculating costs
    ec2_pricing = sum([get_pricing(region, resource=i,
                                   access_key=access_key,
                                   secret_key=secret_key) for i in ec2])
    ec2_costs = (ec2_pricing * total_test_time) / 3600  # Prices are hourly
    print("Found {} EC2 instances, costs are ${}".format(len(ec2), ec2_costs))
    return ec2_costs

def get_volume_costs(ec2_volumes, region, total_test_time, access_key=None,
                     secret_key=None):
    """Calculates and returns total cost of all volumes - both gp2 and io1 types
       Note:For io1 type volumes, price is calculated based on provisioned iops and volume size
            For gp2 type volumes, price is calculated based on volume size only

    Args: ec2_volumes (list): List containing information of all the volumes
                              This can be obtained from aws_discovery.ResourcesDiscovery
          region (str): AWS region
          total_test_time (int): (secs) Total time of test run in Jenkins
          access_key (str): AWS access key ID
          secret_key (str): AWS secret key
    Returns: costs
    """
    if not ec2_volumes:
        th.info("No volumes found! returning costs as 0.")
        return 0
    vol_costs = 0
    size_costs = 0
    iops_costs = 0
    io1_cost = get_pricing(region, resource='io1', access_key=access_key,
                           secret_key=secret_key)
    gp2_cost = get_pricing(region, resource='gp2', access_key=access_key,
                           secret_key=secret_key)

    def _calc_size_costs(size, cost):
        return (size * total_test_time * float(cost)) / timedelta(days=30).total_seconds()
    for volume in ec2_volumes:
        size = volume.description['Size']  # parsing size from CF stack
        iops = volume.description['Iops']  # parsing iops from CF stack
        if volume.description['VolumeType'] == "io1":
            size_costs += _calc_size_costs(size, io1_cost)
            iops_costs += (iops * total_test_time * float(io1_cost)) \
                          / timedelta(days=30).total_seconds()
        elif volume.description['VolumeType'] == "gp2":
            size_costs += _calc_size_costs(size, gp2_cost)
    vol_costs = iops_costs + size_costs
    print("Volume costs are ${}".format(vol_costs))
    return vol_costs


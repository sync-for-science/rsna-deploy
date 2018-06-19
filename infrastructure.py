import time
from botocore.exceptions import ClientError


class SecurityGroup(object):
    pass


def read_settings_file(filename):
    d = {}
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                (key, val) = line.split("=", 1)
                d[key] = val
    return d




def create_security_group(stack_name, ec2_client, vpc):

    print("Creating Security Groups")
    security_group_name = stack_name + '_SG'
    security_group_description = stack_name + ' HTTP/HTTPS/SSH SG'

    try:
        new_security_group = vpc.create_security_group(GroupName=security_group_name, Description=security_group_description)

        time.sleep(5)

        new_security_group.create_tags(Tags=[{'Key': 'Name', 'Value': security_group_name}])
    except ClientError as e:
        new_security_group = SecurityGroup()
        security_group = ec2_client.describe_security_groups(GroupNames=[security_group_name])
        new_security_group.id = security_group["SecurityGroups"][0]["GroupId"]

    return new_security_group


def create_machine_tags(settings, stack_name):

    return [{"Key": "owner", "Value": settings["MACHINE_OWNER"]},
                    {"Key": "Name", "Value": stack_name}]


def create_ec2(ec2, settings, security_group, stack_name):

    print("Creating EC2")
    new_instance = ec2.create_instances(ImageId=settings['AMI_IMAGE_ID'],
                                        MinCount=1,
                                        MaxCount=1,
                                        InstanceType=settings['EC2_INSTANCE_TYPE'],
                                        SecurityGroupIds=[security_group.id],
                                        KeyName=settings['EC2_KEY_NAME'],
                                        SubnetId=settings['SUBNET_ID'],
                                        IamInstanceProfile={"Arn": settings['EC2_IAM_INSTANCE_PROFILE_ARN']},
                                        Placement={'AvailabilityZone': settings['AVAILABILITY_ZONE'],
                                                   'Tenancy': settings['TENANCY']})

    machine_tags = create_machine_tags(settings, stack_name)

    new_instance[0].create_tags(Tags=machine_tags)
    new_instance[0].wait_until_running()

    return new_instance


def create_assign_elastic_ip(stack_name, ec2_client):
    instance_id = get_instance_id(stack_name, ec2_client)
    allocation = ec2_client.allocate_address(Domain='vpc')
    ec2_client.associate_address(AllocationId=allocation['AllocationId'],
                                            InstanceId=instance_id)


def clear_sg_ingresses(ec2_client, stack_name):

    client_security_groups = ec2_client.describe_security_groups(Filters=[{'Name': 'tag:Name', 'Values': [stack_name + '_SG']}])

    # If the SecGroup has Inbound rules then execute
    if len(client_security_groups['SecurityGroups'][0]['IpPermissions']) > 0:
        for permission in client_security_groups['SecurityGroups'][0]['IpPermissions']:
            ec2_client.revoke_security_group_ingress(GroupId=client_security_groups['SecurityGroups'][0]['GroupId'], IpPermissions=[permission])


def add_ingress_to_sg(stack_name, vpc, cidr_ip, from_port, to_port):

    security_group = list(vpc.security_groups.filter(Filters=[{'Name': 'tag:Name', 'Values': [stack_name + '_SG']}]))[0]

    try:
        security_group.authorize_ingress(CidrIp=cidr_ip, FromPort=from_port, ToPort=to_port, IpProtocol="tcp")
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidPermission.Duplicate':
            print("Object already exists")
        else:
            print("Unexpected error: %s" % e)


def get_instance_id(stack_name, ec2_client):
    filters = [{
        'Name': 'tag:Name',
        'Values': [stack_name]}, {
        'Name': 'instance-state-name',
        'Values': ['running']}
    ]

    ecs_ec2_instance1 = ec2_client.describe_instances(Filters=filters)

    return ecs_ec2_instance1['Reservations'][0]['Instances'][0]['InstanceId']


def send_commands(stack_name, ec2_client, ssm_client, commands):

    ec2_instance_id = get_instance_id(stack_name, ec2_client)

    ec2_waiter = ec2_client.get_waiter('instance_status_ok')
    ec2_waiter.wait(InstanceIds=[ec2_instance_id])

    ssm_client.send_command(InstanceIds=[ec2_instance_id],
                            DocumentName="AWS-RunShellScript",
                            Parameters={'commands': commands},
                            OutputS3BucketName='rsna-command-logs',
                            OutputS3KeyPrefix=stack_name)
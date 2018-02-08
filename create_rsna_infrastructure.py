import boto3
from infrastructure import create_ec2, create_security_group, read_settings_file, add_ingress_to_sg, send_commands

import argparse

parser = argparse.ArgumentParser(description='Infrastructure for creating a RSNA server.')

parser.add_argument("--sg",
    help="Create security groups.", action='store_true')
parser.add_argument("--ingress",
    help='Add ingress to security groups.', action='store_true')
parser.add_argument("--ec2",
    help='Create EC2.', action='store_true')
parser.add_argument("--deploy",
    help='Install docker, Pull Repo, and compose.', action='store_true')

args = parser.parse_args()

settings = read_settings_file("settings")
boto3.setup_default_session(profile_name=settings["AWS_CLI_PROFILE_NAME"])
vpc_id = settings["VPC_ID"]

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
vpc = ec2.Vpc(vpc_id)
ssm_client = boto3.client('ssm')

if args.sg:
    security_group = create_security_group("RSNA", ec2_client, vpc)

if args.ingress:
    add_ingress_to_sg(ec2_client, "RSNA", vpc, "0.0.0.0/0", 9090, 9090)

if args.ec2:
    create_ec2(ec2, settings, security_group, "RSNA")

if args.deploy:
    send_commands("RSNA", ec2_client, ssm_client, ["sudo yum update -y && sudo yum install -y git "
                                                   "&& sudo yum install -y docker "
                                                   "&& sudo service docker restart "
                                                   "&& sudo usermod -a -G docker ec2-user"
                                                   "&& sudo curl -L https://github.com/docker/compose/releases/download/1.18.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose"
                                                   "&& sudo chmod +x /usr/local/bin/docker-compose"
                                                   "&& rm -Rf /home/ec2-user/s4s-stack"
                                                   "&& git clone --recursive https://github.com/RSNA/s4s-stack /home/ec2-user/s4s-stack"
                                                   "&& cd /home/ec2-user/s4s-stack"
                                                   "&& git submodule update --init --recursive"
                                                   "&& docker-compose up -d --force-recreate"])





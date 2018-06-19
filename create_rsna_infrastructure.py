import boto3
from infrastructure import create_ec2, \
    create_security_group, \
    read_settings_file, \
    add_ingress_to_sg, \
    send_commands, \
    create_assign_elastic_ip, \
    clear_sg_ingresses

import argparse

parser = argparse.ArgumentParser(description='Infrastructure for creating a RSNA server.')

parser.add_argument("--sg",
    help="Create security groups.", action='store_true')
parser.add_argument("--ingress",
    help='Add ingress to security groups.', action='store_true')
parser.add_argument("--elasticip",
    help='Create Elastic IP.', action='store_true')
parser.add_argument("--ec2",
    help='Create EC2.', action='store_true')
parser.add_argument("--set_up_ec2",
    help='Install docker, docker-compose.', action='store_true')
parser.add_argument("--deploy_proxy",
    help='Start proxy server.', action='store_true')
parser.add_argument("--deploy_rsna",
    help='Start RSNA stack', action='store_true')
parser.add_argument("--loaddata",
    help='Loads test data into running instances.', action='store_true')

args = parser.parse_args()

settings = read_settings_file("settings")
boto3.setup_default_session(profile_name=settings["AWS_CLI_PROFILE_NAME"])
vpc_id = settings["VPC_ID"]

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
vpc = ec2.Vpc(vpc_id)
ssm_client = boto3.client('ssm')

STACK_NAME = "RSNA"

if args.sg:
    security_group = create_security_group(STACK_NAME, ec2_client, vpc)

if args.ingress:

    print("[create_rsna_infrastructure] - Clear all existing Ingress.")
    clear_sg_ingresses(ec2_client, STACK_NAME)

    print("[create_rsna_infrastructure] - Adding Ingress.")
    add_ingress_to_sg(STACK_NAME, vpc, "0.0.0.0/0", 8080, 8080)
    add_ingress_to_sg(STACK_NAME, vpc, "0.0.0.0/0", 80, 80)
    add_ingress_to_sg(STACK_NAME, vpc, "0.0.0.0/0", 443, 443)

if args.ec2:
    create_ec2(ec2, settings, security_group, STACK_NAME)

if args.elasticip:
    create_assign_elastic_ip(STACK_NAME, ec2_client)

if args.set_up_ec2:
    print("[create_rsna_infrastructure] - Setting up EC2.")
    send_commands(STACK_NAME, ec2_client, ssm_client, ["sudo yum update -y && sudo yum install -y git "
                                                       "&& sudo yum install -y docker "
                                                       "&& sudo service docker restart "
                                                       "&& sudo usermod -a -G docker ec2-user"
                                                       "&& sudo curl -L https://github.com/docker/compose/releases/download/1.18.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose"
                                                       "&& sudo chmod +x /usr/local/bin/docker-compose"
                                                       "&& rm -Rf /home/ec2-user/reference-stack-docker"
                                                       "&& git clone --recursive -b 152 https://github.com/sync-for-science/reference-stack-docker /home/ec2-user/reference-stack-docker"
                                                       "&& docker network create nginx-proxy || true"])

if args.deploy_proxy:
    print("[create_rsna_infrastructure] - Deploying Proxy.")
    send_commands(STACK_NAME, ec2_client, ssm_client, ["cd /home/ec2-user/reference-stack-docker/"
                                                       "&& docker-compose -f /home/ec2-user/reference-stack-docker/deploys/demo.syncfor.science/nginx-ssl-proxy/docker-compose.yml down"
                                                       "&& git pull"
                                                       "&& git submodule update --init --recursive"
                                                       "&& docker-compose -f /home/ec2-user/reference-stack-docker/deploys/demo.syncfor.science/nginx-ssl-proxy/docker-compose.yml up -d nginx"
                                                       "&& docker-compose -f /home/ec2-user/reference-stack-docker/deploys/demo.syncfor.science/nginx-ssl-proxy/docker-compose.yml up -d lets-encrypt"])

if args.deploy_rsna:
    print("[create_rsna_infrastructure] - Deploying RSNA Stack.")
    send_commands(STACK_NAME, ec2_client, ssm_client, ["cd /home/ec2-user/reference-stack-docker/"
                                                        "&& git pull"
                                                        "&& git submodule update --init --recursive"
                                                        "&& docker-compose -f /home/ec2-user/reference-stack-docker/docker-builds/s4s-stack/docker-compose.yml -f /home/ec2-user/reference-stack-docker/docker-builds/s4s-stack/docker-compose.override.yml -f /home/ec2-user/reference-stack-docker/deploys/imaging.syncfor.science/docker-compose.override.yml down"
                                                        "&& docker volume prune -f"
                                                        "&& docker-compose -f  /home/ec2-user/reference-stack-docker/docker-builds/s4s-stack/docker-compose.yml -f /home/ec2-user/reference-stack-docker/docker-builds/s4s-stack/docker-compose.override.yml -f /home/ec2-user/reference-stack-docker/deploys/imaging.syncfor.science/docker-compose.override.yml up  -d --force-recreate"])

if args.loaddata:
    send_commands(STACK_NAME, ec2_client, ssm_client, ["cd /home/ec2-user/reference-stack-docker/"
                                                   "&& docker-compose -f /home/ec2-user/reference-stack-docker/docker-builds/s4s-stack/docker-compose.loaddata.yml up"])



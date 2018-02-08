# rsna-deploy

## Creating AWS Resources
### You should only have to do this part once to create the EC2 and associated infrastructure. See the next section when updating the stack.

1. Ensure an instance Role exists that allows an EC2 to use Simple Systems Manager (SSM). Likely easiest to use the
wizard in the console to do this. [Instructions from Amazon.](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-access.html)

2. Create a key pair for use by the EC2 you'll create. Record the name in the settings file.

3. Ensure you have a VPC with subnets to use, record them in the settings file.

4. With settings file populated you can run the python script to create the infrastructure. Toggle the different steps
using the command line arguments. You should also be able to run them all at once.

```shell
python create_rsna_infrastructure.py --sg --ingress --ec2
```

## Deploying Code

1. Running the following will use ssm to send commands to the EC2 to install docker anddocker-compose,
then run the images.

```shell
python create_rsna_infrastructure.py --deploy
```

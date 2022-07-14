import json
from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as sm
)
from constructs import Construct

class MonolithUniTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        # vpc and subnets are defined here
        self.vpc = ec2.Vpc(self, id="monolith-Vpc", max_azs=3, cidr='10.0.0.0/16', 
        nat_gateways=0,
        subnet_configuration=[
            ec2.SubnetConfiguration(
                name="monolith-subnet-public",
                subnet_type=ec2.SubnetType.PUBLIC,
                cidr_mask=24
            ),
            ec2.SubnetConfiguration(
                name="monolith-subnet-private",
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                cidr_mask=24)
        ]
        )

        # public web server security group
        self.sg = ec2.SecurityGroup(self,
            id="monolith-security-group",
            vpc=self.vpc,
            # allow_all_outbound=False
        )

        self.sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(80), description='Allow HTTP from anywhere')
        self.sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(443), description='Allow HTTPS from anywhere')
        # self.sg.add_egress_rule(peer=ec2.Peer.security_group_id(self.sg.security_group_id), connection=ec2.Port.tcp(80), description='Allow HTTP to anywhere')
        # self.sg.add_egress_rule(peer=ec2.Peer.security_group_id(self.sg.security_group_id), connection=ec2.Port.tcp(443),description='Allow HTTPS to anywhere')

        # creating pem file keypair
        # monolith_key = ec2.CfnKeyPair(self,"MyKeyPair",key_name="monolithKey")


        # monolith ec2 instance 
        webserver_ec2_instance = ec2.Instance(self,"monolith-webserver-instance",vpc=self.vpc, 
        instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2,ec2.InstanceSize.NANO),
        machine_image=ec2.MachineImage.generic_linux({
            'us-east-1':'ami-083654bd07b5da81d'}),
        key_name="lnd_hobbit_db_key",
        security_group=self.sg,
        vpc_subnets=ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PUBLIC
        ) )

        # # security group for db
        self.db_sg = ec2.SecurityGroup(self,
            id="monolith-db-sg",
            vpc=self.vpc,
            allow_all_outbound=False
        )

        self.db_sg.add_ingress_rule(peer=ec2.Peer.security_group_id(self.sg.security_group_id), connection=ec2.Port.tcp(3306), description='Allow port 3306 only to the webserver in order to access the MYSQL')
        #create db instance 
        db_instance = rds.DatabaseInstance(
            self,
            "rds-instance",
            engine=rds.DatabaseInstanceEngine.MYSQL,
            instance_identifier="monolith-db-instance",
            deletion_protection=False,
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3,ec2.InstanceSize.MICRO),
            security_groups=[self.db_sg],
            allocated_storage=8,
            credentials=rds.Credentials.from_generated_secret('monolithUser'),
            database_name="monolith_db",
            vpc= self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            
        )


from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    CfnOutput,
    aws_apigateway as api,
    aws_lambda as unicorn_lambda,
    aws_dynamodb as ddb,
    aws_iam as iam 
)
from constructs import Construct


class MonolithUniTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        stage_name = self.node.try_get_context('stage_name')

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
            vpc=self.vpc
        )

        self.sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(80), description='Allow HTTP from anywhere')
        self.sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(443), description='Allow HTTPS from anywhere')
        self.sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(22), description='Allow SSH from anywhere')


        # monolith ec2 instance 
        webserver_ec2_instance = ec2.Instance(self,"monolith-webserver-instance",vpc=self.vpc, 
        instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3,ec2.InstanceSize.SMALL),
        machine_image=ec2.MachineImage.generic_linux({
            'us-east-1':'ami-083654bd07b5da81d'}),
        key_name="lnd_hobbit_db_key",
        security_group=self.sg,
        vpc_subnets=ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PUBLIC
        ))
        
        with open('./lib/post_initialization.sh', 'r', encoding='utf-8') as file:
            webserver_ec2_instance.add_user_data(file.read())

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

        # basket Dynamodb 
        basket_table = ddb.Table(self, f"basket-db-{stage_name}",table_name=f'basket_db_{stage_name}', partition_key={
            'name': 'id',
            'type': ddb.AttributeType.STRING
        },
        billing_mode=ddb.BillingMode.PAY_PER_REQUEST)

        basket_table.add_global_secondary_index(
            index_name="userIdIndexName",
            partition_key= ddb.Attribute(
            name="uuid",
            type=ddb.AttributeType.STRING
            )
        )

        # basket lambda for unicorn 
        basket_lambda = unicorn_lambda.Function(self,f'BasketHandler-{stage_name}',runtime=unicorn_lambda.Runtime.PYTHON_3_9,
        handler='basket_lambda.handler',
        function_name=f"basket-lambda-{stage_name}",
        code=unicorn_lambda.Code.from_asset('./lib/lambda/basket_lambda'),
        environment={
            'BASKET_TABLE_NAME': basket_table.table_name,
        }
        )
        #get basket based on user id
        get_basket_lambda = unicorn_lambda.Function(self,f'GetBasketHandler-{stage_name}',runtime=unicorn_lambda.Runtime.PYTHON_3_9,
        handler='get_basket.handler',
        function_name=f"get-basket-lambda-{stage_name}",
        code=unicorn_lambda.Code.from_asset('./lib/lambda/basket_lambda'),
        environment={
            'BASKET_TABLE_NAME': basket_table.table_name,
            'BASKET_INDEX_NAME': "userIdIndexName"
        }
        )
        #delete basket by adding id
        delete_basket_lambda = unicorn_lambda.Function(self,f'DeleteBasketHandler-{stage_name}',runtime=unicorn_lambda.Runtime.PYTHON_3_9,
        handler='delete_basket.handler',
        function_name=f"delete-basket-lambda-{stage_name}",
        code=unicorn_lambda.Code.from_asset('./lib/lambda/basket_lambda'),
        environment={
            'BASKET_TABLE_NAME': basket_table.table_name,
        }
        )

        # giving permission to lambda to access the table
        basket_table.grant_write_data(basket_lambda)
        basket_table.grant_read_data(get_basket_lambda)
        basket_table.grant_read_write_data(delete_basket_lambda)

        #basket lambda policystatement
        basket_table_policy = iam.PolicyStatement(
            actions=[
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:Query",
                "dynamodb:DeleteItem",
                "dynamodb:Scan"
            ],
            resources=[basket_table.table_arn]
        )

        # Attaching the inline policy to the role
        basket_lambda.role.attach_inline_policy(policy=iam.Policy(self,f'{stage_name}-basket_table_permissions',statements=[basket_table_policy]))

        get_basket_lambda.role.attach_inline_policy(policy=iam.Policy(self,f'{stage_name}-get_basket_table_permissions',statements=[basket_table_policy]))

        delete_basket_lambda.role.attach_inline_policy(policy=iam.Policy(self,f'{stage_name}-delete_basket_table_permissions',statements=[basket_table_policy]))


         # Adding Api Gateway with Http 
        uni_api = api.RestApi(self, f"unicorn_api_{stage_name}", rest_api_name=f"unicorn_api_{stage_name}", 
        deploy_options=api.StageOptions(stage_name=f'{stage_name}'),
        default_cors_preflight_options=api.CorsOptions(
            allow_headers=['Content-Type','X-Amx-Date'],
            allow_methods=['GET','POST','DELETE'],
            allow_origins=['*']
        )
         )

        create_basket_integration = api.LambdaIntegration(basket_lambda)
        get_basket_integration = api.LambdaIntegration(get_basket_lambda)
        delete_basket_integration = api.LambdaIntegration(delete_basket_lambda)

        unicorn = uni_api.root.add_resource('unicorns')
        # endpoint for unicorn
        unicorn.add_method("POST",integration=api.HttpIntegration("http://mono-to-micro-bucket.s3-website-us-east-1.amazonaws.com/"))
        unicorn.add_method("GET",integration=api.HttpIntegration("http://mono-to-micro-bucket.s3-website-us-east-1.amazonaws.com/"))

        # endpoint for instance health check
        health_check = uni_api.root.add_resource('health')
        ping_endpoint = health_check.add_resource('ping')
        is_healthy_endpoint = health_check.add_resource('ishealthy')
        db_ping_endpoint = health_check.add_resource('dbping')
        ping_endpoint.add_method("GET",integration=api.HttpIntegration("http://mono-to-micro-bucket.s3-website-us-east-1.amazonaws.com/"))
        is_healthy_endpoint.add_method("GET",integration=api.HttpIntegration("http://mono-to-micro-bucket.s3-website-us-east-1.amazonaws.com/"))
        db_ping_endpoint.add_method("GET",integration=api.HttpIntegration("http://mono-to-micro-bucket.s3-website-us-east-1.amazonaws.com/"))

        # endpoint for user
        user_endpoint = uni_api.root.add_resource('user')
        login_endpoint = user_endpoint.add_resource('login')
        user_endpoint.add_method("POST",integration=api.HttpIntegration("http://mono-to-micro-bucket.s3-website-us-east-1.amazonaws.com/"))
        login_endpoint.add_method("POST", integration=api.HttpIntegration("http://mono-to-micro-bucket.s3-website-us-east-1.amazonaws.com/"))


       # endpoints for basket
        unicorn_basket = unicorn.add_resource('basket')
        with_user_uuid = unicorn_basket.add_resource('{user_uuid}')
        with_user_uuid.add_method("GET",integration=get_basket_integration)
        unicorn_basket.add_method("POST",integration=create_basket_integration)
        unicorn_basket.add_method("DELETE",integration=delete_basket_integration)

        #Outputs
        CfnOutput(self,"unicorn-api",description="Unicorn endpoint", value=uni_api.url_for_path())

        CfnOutput(self,"unicorn-lambda", description="Basket Lambda", value=basket_lambda.function_name)

        CfnOutput(self, "my_db_instance", description="Unicorn RDS DB", value=db_instance.db_instance_endpoint_address)
        

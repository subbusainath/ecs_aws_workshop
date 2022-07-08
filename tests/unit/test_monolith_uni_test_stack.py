import aws_cdk as core
import aws_cdk.assertions as assertions

from monolith_uni_test.monolith_uni_test_stack import MonolithUniTestStack

# example tests. To run these tests, uncomment this file along with the example
# resource in monolith_uni_test/monolith_uni_test_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MonolithUniTestStack(app, "monolith-uni-test")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

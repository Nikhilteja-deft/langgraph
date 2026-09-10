from langchain_aws import ChatBedrockConverse

# max_retries=0 prevents botocore from sleeping/retrying 9 times on throttle
model = ChatBedrockConverse(
    model_id="us.amazon.nova-pro-v1:0",
    region_name="us-east-1",
    max_retries=0
)

try:
    response = model.invoke("Say hello in one sentence.")
    print(response.content)
except Exception as e:
    print(f"AWS Bedrock Error: {e}")


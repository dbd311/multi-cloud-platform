import os
import boto3
from google.cloud import dns
from azure.mgmt.dns import DnsManagementClient
from azure.identity import DefaultAzureCredential
from kubernetes import client, config


# Create DNS record for a given cloud provider and domain.

def create_dns_record(provider, domain, ip_address):
    if provider == "aws":
        client = boto3.client('route53')
        hosted_zone_id = os.getenv('AWS_HOSTED_ZONE_ID')
        client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={'Changes': [{'Action': 'UPSERT', 'ResourceRecordSet': {
                'Name': domain, 'Type': 'A', 'TTL': 300, 'ResourceRecords': [{'Value': ip_address}]
            }}]}
        )
    elif provider == "gcp":
        client = dns.Client()
        zone = client.zone(os.getenv('GCP_DNS_ZONE_NAME'))
        record_set = zone.resource_record_set(domain, 'A', 300, [ip_address])
        changes = zone.changes()
        changes.add_record_set(record_set)
        changes.create()
    elif provider == "azure":
        credential = DefaultAzureCredential()
        dns_client = DnsManagementClient(credential, os.getenv('AZURE_SUBSCRIPTION_ID'))
        dns_client.record_sets.delete(os.getenv('AZURE_DNS_RESOURCE_GROUP'), os.getenv('AZURE_DNS_ZONE_NAME'), domain, 'A')


# Delete DNS record for a given cloud provider and domain.
def delete_dns_record(provider, domain, namespace, app_name):

    try:
        # Get the external IP address of the ingress corresponding to the app_name in the given namespace
        networking_v1 = client.NetworkingV1Api()
        ingress = networking_v1.read_namespaced_ingress(
            name=app_name, namespace=namespace
        )
        ingress_ip = ingress.status.load_balancer.ingress[0].ip

        if not ingress_ip:
            raise ValueError("No ingress IP found for this deployment")

        if provider == "aws":
            hosted_zone_id = os.getenv('AWS_HOSTED_ZONE_ID')
            client = boto3.client('route53')

            response = client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': {
                                'Name': domain,
                                'Type': 'A',
                                'TTL': 300,
                                'ResourceRecords': [{'Value': ingress_ip}]
                            }
                        }
                    ]
                }
            )
            return response

        elif provider == "gcp":
            client = dns.Client()
            zone = client.zone(os.getenv('GCP_DNS_ZONE_NAME'))

            record_set = zone.resource_record_set(domain, 'A', 300, [ingress_ip])
            changes = zone.changes()
            changes.delete_record_set(record_set)
            changes.create()
            return changes

        elif provider == "azure":
            credential = DefaultAzureCredential()
            subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
            resource_group = os.getenv('AZURE_DNS_RESOURCE_GROUP')
            zone_name = os.getenv('AZURE_DNS_ZONE_NAME')

            dns_client = DnsManagementClient(credential, subscription_id)
            dns_client.record_sets.delete(resource_group, zone_name, domain, 'A')

        else:
            raise ValueError(f"Unsupported cloud provider: {provider}")

        return {"status": "DNS record deleted successfully"}

    except Exception as e:
        return {"error": f"Failed to delete DNS record: {str(e)}"}


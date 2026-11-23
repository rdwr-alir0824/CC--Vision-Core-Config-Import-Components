"""Development/test fixtures only; 0.0-test is never a real product version."""

from .capabilities import CapabilityDeclaration, LookupCapability, ReadCapability


MOCK_CAPABILITIES = (
    CapabilityDeclaration(
        "cyber-controller", "0.0-test", ReadCapability.PHYSICAL_TREE,
        ("mgmt", "system", "config", "tree", "Physical"), "API-02",
        qualification="synthetic-mock-only", response_schema="synthetic-unverified",
    ),
    CapabilityDeclaration(
        "cyber-controller", "0.0-test", ReadCapability.ORGANIZATION_TREE,
        ("mgmt", "system", "config", "tree", "Organization"), "API-03",
        qualification="synthetic-mock-only", response_schema="synthetic-unverified",
    ),
    CapabilityDeclaration(
        "vision", "0.0-test", ReadCapability.LDAP_PERMISSIONS,
        ("mgmt", "system", "config", "itemlist", "ldapobjectpermission"), "API-10",
        qualification="synthetic-mock-only", response_schema="synthetic-unverified",
    ),
    CapabilityDeclaration(
        "cyber-controller", "0.0-test", LookupCapability.SITE_BY_NAME,
        ("mgmt", "system", "config", "tree", "site", "byname", "{name}"), "API-04",
        qualification="synthetic-mock-only", response_schema="synthetic-unverified",
    ),
    CapabilityDeclaration(
        "cyber-controller", "0.0-test", LookupCapability.SITE_BY_ID,
        ("mgmt", "system", "config", "tree", "site", "byid", "{id}"), "API-05",
        qualification="synthetic-mock-only", response_schema="synthetic-unverified",
    ),
    CapabilityDeclaration(
        "cyber-controller", "0.0-test", LookupCapability.DEVICE_BY_IP,
        ("mgmt", "system", "config", "tree", "device", "byip", "{ip}"), "API-06",
        qualification="synthetic-mock-only", response_schema="synthetic-unverified",
    ),
)

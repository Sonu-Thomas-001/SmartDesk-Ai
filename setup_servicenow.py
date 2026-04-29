"""
Setup script: Creates 10+ support groups and sample incidents in ServiceNow.
Run once to seed your instance with test data.
"""

import requests
import time

INSTANCE_URL = "https://dev375174.service-now.com"
AUTH = ("admin", "QqzK=G*27Pvh")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

# ---------------------------------------------------------------------------
# 10+ Support Groups with descriptions
# ---------------------------------------------------------------------------
SUPPORT_GROUPS = [
    {"name": "Network Operations", "description": "Handles network connectivity, VPN, firewall, and routing issues"},
    {"name": "Desktop Support", "description": "Manages hardware, peripherals, OS issues, and workstation troubleshooting"},
    {"name": "Application Support", "description": "Supports enterprise applications including ERP, CRM, and custom apps"},
    {"name": "IAM Team", "description": "Identity and Access Management - user provisioning, password resets, role assignments"},
    {"name": "Security Operations", "description": "Incident response, vulnerability management, threat detection"},
    {"name": "Database Administration", "description": "Database performance, backup/recovery, schema changes, and SQL issues"},
    {"name": "Cloud Infrastructure", "description": "AWS/GCP/Azure resource management, VM provisioning, cloud migrations"},
    {"name": "Email & Collaboration", "description": "Email systems, Microsoft 365, Teams, SharePoint administration"},
    {"name": "Service Desk L1", "description": "First-level support, ticket triage, basic troubleshooting"},
    {"name": "DevOps Engineering", "description": "CI/CD pipelines, deployment automation, container orchestration"},
    {"name": "Telecom & Unified Communications", "description": "Phone systems, video conferencing, SIP trunks, call routing"},
    {"name": "Data Center Operations", "description": "Physical infrastructure, power, cooling, rack management"},
]

# ---------------------------------------------------------------------------
# Sample incidents (diverse types to match support groups)
# ---------------------------------------------------------------------------
SAMPLE_INCIDENTS = [
    {
        "short_description": "VPN disconnects every 10 minutes when working from home",
        "description": "Multiple users from the finance department report that VPN connection drops every 10 minutes. They have to reconnect manually each time. This started after the last firewall update on Friday.",
        "category": "Network",
        "caller_id": "admin",
        "urgency": "2",
        "impact": "2",
    },
    {
        "short_description": "Laptop blue screen after Windows update",
        "description": "My Dell Latitude 5520 is showing BSOD with error KERNEL_DATA_INPAGE_ERROR after installing KB5034441 update. Cannot boot into Windows. Need urgent fix as I have client presentations this week.",
        "category": "Hardware",
        "caller_id": "admin",
        "urgency": "2",
        "impact": "3",
    },
    {
        "short_description": "SAP transaction timeout during month-end close",
        "description": "SAP ERP transaction FB50 is timing out when trying to post journal entries. The month-end close process is blocked. Error: Connection to application server timed out. Multiple users in accounting are affected.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "1",
        "impact": "1",
    },
    {
        "short_description": "New employee needs Active Directory account and email",
        "description": "New hire John Smith starting on Monday in Marketing department. Needs AD account, email setup, access to SharePoint marketing site, and CRM read access. Manager: Jane Doe.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "3",
        "impact": "3",
    },
    {
        "short_description": "Suspicious emails received by multiple executives",
        "description": "5 C-level executives received spear phishing emails pretending to be from our CEO requesting wire transfers. The emails passed spam filters. Sender domain is similar to ours but uses a zero instead of O.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "1",
        "impact": "1",
    },
    {
        "short_description": "Production database running out of disk space",
        "description": "Oracle production database FINDB01 is at 92% disk capacity. Growth rate suggests it will hit 100% within 48 hours. Need to extend tablespace or archive old data immediately.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "1",
        "impact": "2",
    },
    {
        "short_description": "AWS EC2 instances in us-east-1 are unreachable",
        "description": "All 15 EC2 instances in the us-east-1 production cluster are showing status check failures. Our customer-facing API is returning 502 errors. CloudWatch shows network interface issues started at 3:45 AM.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "1",
        "impact": "1",
    },
    {
        "short_description": "Cannot send emails with attachments larger than 5MB",
        "description": "Since yesterday, all users are getting bounce-back errors when sending emails with attachments over 5MB. Previously the limit was 25MB. No configuration changes were made intentionally. Exchange Online.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "2",
        "impact": "2",
    },
    {
        "short_description": "Password reset not working from self-service portal",
        "description": "The self-service password reset portal returns 'Service Unavailable' error. Around 50 users per day use this. IT helpdesk is getting flooded with manual reset requests. SSPR connector seems to be down.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "2",
        "impact": "2",
    },
    {
        "short_description": "Jenkins build pipeline failing after plugin update",
        "description": "All Jenkins CI/CD pipelines are failing with 'java.lang.NoClassDefFoundError: pipeline-model-definition'. This started after the automatic plugin update last night. 12 development teams are blocked from deploying.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "1",
        "impact": "1",
    },
    {
        "short_description": "Conference room phone system has no dial tone",
        "description": "All 8 conference room phones on the 3rd floor have no dial tone. The SIP trunk seems to be down. Video conferencing via Zoom still works but clients cannot dial into conference bridges.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "2",
        "impact": "2",
    },
    {
        "short_description": "Server room temperature alarm triggered",
        "description": "DCIM alert: Server room B temperature reached 28°C (threshold is 25°C). One of the CRAC units appears to have failed. If not resolved quickly, servers may auto-shutdown to prevent damage.",
        "category": "Hardware",
        "caller_id": "admin",
        "urgency": "1",
        "impact": "1",
    },
    {
        "short_description": "Need access to Salesforce for new sales team members",
        "description": "Three new sales reps (Amy Chen, Bob Martinez, Carol White) need Salesforce CRM access with 'Sales Rep' profile. They also need Slack channels #sales-team and #deals-pipeline. Start date: next Monday.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "3",
        "impact": "3",
    },
    {
        "short_description": "Website loading extremely slow for customers",
        "description": "Customer-facing website response time increased from 200ms to 8 seconds. Google Analytics shows 60% bounce rate increase. The issue seems to be with the CDN or load balancer. Revenue impact estimated at $5000/hour.",
        "category": "Software",
        "caller_id": "admin",
        "urgency": "1",
        "impact": "1",
    },
    {
        "short_description": "Printer on 2nd floor printing garbled text",
        "description": "The HP LaserJet on 2nd floor near accounting is printing garbled characters on every document. Restarted the printer and cleared the queue but issue persists. May need driver reinstall or firmware update.",
        "category": "Hardware",
        "caller_id": "admin",
        "urgency": "3",
        "impact": "3",
    },
]


def create_group(session: requests.Session, group: dict) -> str | None:
    """Create an assignment group in ServiceNow. Returns sys_id or None if exists."""
    # Check if group already exists
    check = session.get(
        f"{INSTANCE_URL}/api/now/table/sys_user_group",
        params={"sysparm_query": f"name={group['name']}", "sysparm_fields": "sys_id,name"},
        timeout=30,
    )
    check.raise_for_status()
    existing = check.json().get("result", [])
    if existing:
        print(f"  [EXISTS] {group['name']} (sys_id={existing[0]['sys_id']})")
        return existing[0]["sys_id"]

    resp = session.post(
        f"{INSTANCE_URL}/api/now/table/sys_user_group",
        json={"name": group["name"], "description": group["description"]},
        timeout=30,
    )
    resp.raise_for_status()
    sys_id = resp.json()["result"]["sys_id"]
    print(f"  [CREATED] {group['name']} (sys_id={sys_id})")
    return sys_id


def create_incident(session: requests.Session, incident: dict) -> str | None:
    """Create an incident in ServiceNow. Returns sys_id."""
    resp = session.post(
        f"{INSTANCE_URL}/api/now/table/incident",
        json=incident,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()["result"]
    print(f"  [CREATED] {result['number']} — {incident['short_description'][:50]}")
    return result["sys_id"]


def main():
    session = requests.Session()
    session.auth = AUTH
    session.headers.update(HEADERS)

    print("=" * 60)
    print("SETTING UP SERVICENOW — SUPPORT GROUPS")
    print("=" * 60)
    for group in SUPPORT_GROUPS:
        try:
            create_group(session, group)
        except Exception as e:
            print(f"  [ERROR] {group['name']}: {e}")
        time.sleep(0.3)

    print("\n" + "=" * 60)
    print("CREATING SAMPLE INCIDENTS")
    print("=" * 60)
    for inc in SAMPLE_INCIDENTS:
        try:
            create_incident(session, inc)
        except Exception as e:
            print(f"  [ERROR] {inc['short_description'][:40]}: {e}")
        time.sleep(0.3)

    print("\n✅ Setup complete! Restart SmartDesk AI and poll to process these incidents.")


if __name__ == "__main__":
    main()

"""
Setup script: Creates assignment groups, lead users and memberships in ServiceNow.
Run once to seed your instance with the SmartDesk AI team structure.
"""

import requests
import time

INSTANCE_URL = "https://dev375174.service-now.com"
AUTH = ("admin", "QqzK=G*27Pvh")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

# ---------------------------------------------------------------------------
# Team roster — must match TEAM_ROSTER in decision_engine.py
# ---------------------------------------------------------------------------
TEAMS = [
    {
        "name": "Network Team",
        "description": "Handles network, VPN, firewall, DNS, and connectivity issues",
        "members": [
            {"first": "Alice",   "last": "Johnson",  "email": "alice.johnson@smartdesk.dev",  "lead": True},
            {"first": "Bob",     "last": "Martinez", "email": "bob.martinez@smartdesk.dev",   "lead": False},
        ],
    },
    {
        "name": "Application Support",
        "description": "Software bugs, app crashes, email, ERP, CRM support",
        "members": [
            {"first": "Charlie", "last": "Kim",      "email": "charlie.kim@smartdesk.dev",    "lead": True},
            {"first": "Diana",   "last": "Patel",    "email": "diana.patel@smartdesk.dev",    "lead": False},
        ],
    },
    {
        "name": "IAM Team",
        "description": "Identity and Access Management — provisioning, passwords, SSO",
        "members": [
            {"first": "Ethan",   "last": "Brooks",   "email": "ethan.brooks@smartdesk.dev",   "lead": True},
            {"first": "Fiona",   "last": "Chen",     "email": "fiona.chen@smartdesk.dev",     "lead": False},
        ],
    },
    {
        "name": "Security Team",
        "description": "Security incidents, malware, data breaches, threat response",
        "members": [
            {"first": "Grace",   "last": "Lee",      "email": "grace.lee@smartdesk.dev",      "lead": True},
            {"first": "Hassan",  "last": "Ali",      "email": "hassan.ali@smartdesk.dev",     "lead": False},
        ],
    },
    {
        "name": "Hardware Support",
        "description": "Laptops, monitors, printers, peripherals, hardware failures",
        "members": [
            {"first": "Isaac",   "last": "Turner",   "email": "isaac.turner@smartdesk.dev",   "lead": True},
            {"first": "Julia",   "last": "Reyes",    "email": "julia.reyes@smartdesk.dev",    "lead": False},
        ],
    },
    {
        "name": "Database Team",
        "description": "Database errors, performance tuning, backups, SQL, data issues",
        "members": [
            {"first": "Kevin",   "last": "Nakamura", "email": "kevin.nakamura@smartdesk.dev", "lead": True},
            {"first": "Laura",   "last": "Singh",    "email": "laura.singh@smartdesk.dev",    "lead": False},
        ],
    },
    {
        "name": "Cloud Infrastructure",
        "description": "Cloud VMs, storage, AWS/Azure/GCP, Kubernetes, DevOps",
        "members": [
            {"first": "Michael", "last": "Okonkwo",  "email": "michael.okonkwo@smartdesk.dev","lead": True},
            {"first": "Natalie", "last": "Dubois",   "email": "natalie.dubois@smartdesk.dev", "lead": False},
        ],
    },
    {
        "name": "Service Desk",
        "description": "General queries, first-level support, fallback triage",
        "members": [
            {"first": "Oliver",  "last": "Grant",    "email": "oliver.grant@smartdesk.dev",   "lead": True},
            {"first": "Priya",   "last": "Sharma",   "email": "priya.sharma@smartdesk.dev",   "lead": False},
        ],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_or_create_user(session: requests.Session, user: dict) -> str:
    """Find or create a sys_user. Returns sys_id."""
    user_name = f"{user['first'].lower()}.{user['last'].lower()}"

    # Check if user exists
    check = session.get(
        f"{INSTANCE_URL}/api/now/table/sys_user",
        params={"sysparm_query": f"user_name={user_name}", "sysparm_fields": "sys_id,user_name"},
        timeout=30,
    )
    check.raise_for_status()
    existing = check.json().get("result", [])
    if existing:
        print(f"    [EXISTS] {user['first']} {user['last']} ({existing[0]['sys_id']})")
        return existing[0]["sys_id"]

    # Create user
    payload = {
        "user_name": user_name,
        "first_name": user["first"],
        "last_name": user["last"],
        "email": user["email"],
        "active": "true",
    }
    resp = session.post(
        f"{INSTANCE_URL}/api/now/table/sys_user",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    sys_id = resp.json()["result"]["sys_id"]
    print(f"    [CREATED] {user['first']} {user['last']} ({sys_id})")
    return sys_id


def find_or_create_group(session: requests.Session, name: str, description: str) -> str:
    """Find or create a sys_user_group. Returns sys_id."""
    check = session.get(
        f"{INSTANCE_URL}/api/now/table/sys_user_group",
        params={"sysparm_query": f"name={name}", "sysparm_fields": "sys_id,name"},
        timeout=30,
    )
    check.raise_for_status()
    existing = check.json().get("result", [])
    if existing:
        print(f"  [EXISTS] {name} ({existing[0]['sys_id']})")
        return existing[0]["sys_id"]

    resp = session.post(
        f"{INSTANCE_URL}/api/now/table/sys_user_group",
        json={"name": name, "description": description},
        timeout=30,
    )
    resp.raise_for_status()
    sys_id = resp.json()["result"]["sys_id"]
    print(f"  [CREATED] {name} ({sys_id})")
    return sys_id


def set_group_manager(session: requests.Session, group_sys_id: str, manager_sys_id: str, group_name: str):
    """Set the manager field on the group."""
    resp = session.patch(
        f"{INSTANCE_URL}/api/now/table/sys_user_group/{group_sys_id}",
        json={"manager": manager_sys_id},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"  [MANAGER SET] {group_name}")


def add_group_member(session: requests.Session, group_sys_id: str, user_sys_id: str, user_name: str):
    """Add a user to a group via sys_user_grmember table."""
    # Check if membership exists
    check = session.get(
        f"{INSTANCE_URL}/api/now/table/sys_user_grmember",
        params={
            "sysparm_query": f"group={group_sys_id}^user={user_sys_id}",
            "sysparm_fields": "sys_id",
        },
        timeout=30,
    )
    check.raise_for_status()
    if check.json().get("result"):
        print(f"    [MEMBER EXISTS] {user_name}")
        return

    resp = session.post(
        f"{INSTANCE_URL}/api/now/table/sys_user_grmember",
        json={"group": group_sys_id, "user": user_sys_id},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"    [MEMBER ADDED] {user_name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    session = requests.Session()
    session.auth = AUTH
    session.headers.update(HEADERS)

    print("=" * 60)
    print("SETTING UP SERVICENOW — GROUPS, USERS & MEMBERSHIPS")
    print("=" * 60)

    for team in TEAMS:
        print(f"\n--- {team['name']} ---")

        # 1. Create or find the group
        group_sid = find_or_create_group(session, team["name"], team["description"])
        time.sleep(0.3)

        lead_sid = None

        # 2. Create or find each member and add to group
        for member in team["members"]:
            user_sid = find_or_create_user(session, member)
            time.sleep(0.3)

            add_group_member(session, group_sid, user_sid, f"{member['first']} {member['last']}")
            time.sleep(0.3)

            if member.get("lead"):
                lead_sid = user_sid

        # 3. Set the lead as manager of the group
        if lead_sid:
            set_group_manager(session, group_sid, lead_sid, team["name"])
            time.sleep(0.3)

    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print("8 groups created with 16 users and group memberships.")
    print("Each group has a manager (lead) assigned.")


if __name__ == "__main__":
    main()

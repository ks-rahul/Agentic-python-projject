#!/usr/bin/env python
"""Database seeder CLI."""
import asyncio
import argparse
import sys

from app.db.postgresql import AsyncSessionLocal
from app.db.seeders import (
    RolePermissionSeeder,
    PermissionSeeder,
    UserSeeder,
    SuperAdminSeeder,
    AppModuleSeeder,
    ChatBuilderSeeder,
    LeadFormSeeder,
    LeadSeeder,
)


async def seed_app_modules():
    """Seed app modules."""
    async with AsyncSessionLocal() as db:
        seeder = AppModuleSeeder(db)
        result = await seeder.seed()
        
        print("\n✅ App Modules seeded successfully!")
        print(f"   Modules created: {result['modules_created']}")
        print(f"   Modules skipped: {result['modules_skipped']}")


async def seed_permissions():
    """Seed permissions with app module support."""
    async with AsyncSessionLocal() as db:
        seeder = PermissionSeeder(db)
        result = await seeder.seed()
        
        print("\n✅ Permissions seeded successfully!")
        print(f"   Permissions created: {result['permissions_created']}")
        print(f"   Permissions updated: {result['permissions_updated']}")
        print(f"   Permissions skipped: {result['permissions_skipped']}")


async def seed_roles_permissions():
    """Seed roles and permissions."""
    async with AsyncSessionLocal() as db:
        seeder = RolePermissionSeeder(db)
        result = await seeder.seed()
        
        print("\n✅ Roles and Permissions seeded successfully!")
        print(f"   Permissions created: {result['permissions_created']}")
        print(f"   Permissions skipped: {result['permissions_skipped']}")
        print(f"   Roles created: {result['roles_created']}")
        print(f"   Roles skipped: {result['roles_skipped']}")
        print(f"   Role-Permission links: {result['role_permissions_attached']}")


async def seed_users():
    """Seed default users."""
    async with AsyncSessionLocal() as db:
        seeder = UserSeeder(db)
        result = await seeder.seed()
        
        print("\n✅ Users seeded successfully!")
        print(f"   Users created: {result['users_created']}")
        print(f"   Users skipped: {result['users_skipped']}")
        print(f"   Tenants created: {result['tenants_created']}")
        print(f"   Roles assigned: {result['roles_assigned']}")
        print(f"   Permissions assigned: {result['permissions_assigned']}")


async def seed_superadmin():
    """Seed only superadmin user."""
    async with AsyncSessionLocal() as db:
        seeder = SuperAdminSeeder(db)
        result = await seeder.seed()
        
        print("\n✅ Super Admin seeded successfully!")
        print(f"   Users created: {result['users_created']}")
        print(f"   Users skipped: {result['users_skipped']}")


async def seed_chat_builders(tenant_id: str = None):
    """Seed default chat builders."""
    async with AsyncSessionLocal() as db:
        seeder = ChatBuilderSeeder(db)
        result = await seeder.seed(tenant_id=tenant_id)
        
        print("\n✅ Chat Builders seeded successfully!")
        print(f"   Chat builders created: {result['chat_builders_created']}")
        print(f"   Chat builders skipped: {result['chat_builders_skipped']}")


async def seed_lead_forms(tenant_id: str = None, agent_id: str = None):
    """Seed default lead forms."""
    async with AsyncSessionLocal() as db:
        seeder = LeadFormSeeder(db)
        result = await seeder.seed(tenant_id=tenant_id, agent_id=agent_id)
        
        print("\n✅ Lead Forms seeded successfully!")
        print(f"   Lead forms created: {result['lead_forms_created']}")
        print(f"   Lead forms skipped: {result['lead_forms_skipped']}")


async def seed_leads():
    """Seed lead module and permissions."""
    async with AsyncSessionLocal() as db:
        seeder = LeadSeeder(db)
        result = await seeder.seed()
        
        print("\n✅ Leads seeded successfully!")
        print(f"   Module created: {result['module_created']}")
        print(f"   Module skipped: {result['module_skipped']}")
        print(f"   Permissions created: {result['permissions_created']}")
        print(f"   Permissions skipped: {result['permissions_skipped']}")
        print(f"   Role-Permission links: {result['role_permissions_attached']}")


async def seed_all():
    """Run all seeders in correct order."""
    print("🌱 Running all seeders...")
    
    # 1. App Modules first (for permission grouping)
    await seed_app_modules()
    
    # 2. Permissions with app module support
    await seed_permissions()
    
    # 3. Roles and Role-Permission links
    await seed_roles_permissions()
    
    # 4. Lead module and permissions (depends on roles)
    await seed_leads()
    
    # 5. Users (depends on roles)
    await seed_users()
    
    # 6. Chat Builders (depends on tenants)
    await seed_chat_builders()
    
    # 7. Lead Forms (depends on tenants and agents)
    # Note: Lead forms require an agent, so they may be skipped if no agents exist
    await seed_lead_forms()


async def seed_fresh():
    """Fresh seed - truncate and reseed (use with caution!)."""
    print("⚠️  Fresh seeding - this will reset seeded data...")
    # For now, just run all seeders (they use updateOrCreate logic)
    await seed_all()


def main():
    parser = argparse.ArgumentParser(
        description="Database seeder for Agentic AI Python Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed.py                    # Run all seeders
  python seed.py all                # Run all seeders
  python seed.py roles              # Seed roles and permissions only
  python seed.py users              # Seed users only
  python seed.py superadmin         # Seed superadmin user only
  python seed.py modules            # Seed app modules only
  python seed.py chat-builders      # Seed chat builders only
  python seed.py lead-forms         # Seed lead forms only
  python seed.py fresh              # Fresh seed (reset and reseed)
        """
    )
    parser.add_argument(
        "seeder",
        nargs="?",
        default="all",
        choices=[
            "all", 
            "roles", 
            "permissions", 
            "users", 
            "superadmin",
            "modules",
            "leads",
            "chat-builders",
            "lead-forms",
            "fresh"
        ],
        help="Which seeder to run (default: all)"
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        help="Tenant ID for tenant-specific seeders"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Agent ID for agent-specific seeders"
    )
    
    args = parser.parse_args()
    
    print(f"🌱 Running seeder: {args.seeder}")
    
    try:
        if args.seeder == "all":
            asyncio.run(seed_all())
        elif args.seeder in ["roles", "permissions"]:
            asyncio.run(seed_roles_permissions())
        elif args.seeder == "users":
            asyncio.run(seed_users())
        elif args.seeder == "superadmin":
            asyncio.run(seed_superadmin())
        elif args.seeder == "modules":
            asyncio.run(seed_app_modules())
        elif args.seeder == "leads":
            asyncio.run(seed_leads())
        elif args.seeder == "chat-builders":
            asyncio.run(seed_chat_builders(args.tenant_id))
        elif args.seeder == "lead-forms":
            asyncio.run(seed_lead_forms(args.tenant_id, args.agent_id))
        elif args.seeder == "fresh":
            asyncio.run(seed_fresh())
        
        print("\n✨ Seeding complete!")
        
    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

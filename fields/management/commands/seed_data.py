"""Populate the database with representative demo data for dashboards and tests."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from fields.models import Field, FieldUpdate


class Command(BaseCommand):
    """Create a reproducible demo dataset for the SmartSeason app."""

    help = 'Seed the database with demo data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Create admin
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@smartseason.io',
                'first_name': 'Grace',
                'last_name': 'Kamau',
                'role': User.Role.ADMIN,
                'is_staff': True,
            }
        )
        admin.set_password('admin1234')
        admin.save()

        # Create field agents
        agent1, _ = User.objects.get_or_create(
            username='agent_james',
            defaults={
                'email': 'james@smartseason.io',
                'first_name': 'James',
                'last_name': 'Oduya',
                'role': User.Role.FIELD_AGENT,
            }
        )
        agent1.set_password('agent1234')
        agent1.save()

        agent2, _ = User.objects.get_or_create(
            username='agent_wanjiru',
            defaults={
                'email': 'wanjiru@smartseason.io',
                'first_name': 'Wanjiru',
                'last_name': 'Mwangi',
                'role': User.Role.FIELD_AGENT,
            }
        )
        agent2.set_password('agent1234')
        agent2.save()

        today = timezone.now().date()

        # Seed data intentionally covers every stage and status combination used by the UI.
        seed_fields = [
            # Active fields
            {
                'name': 'North Plot A',
                'crop_type': 'Maize',
                'planting_date': today - timedelta(days=30),
                'current_stage': Field.Stage.GROWING,
                'assigned_agent': agent1,
            },
            {
                'name': 'East Block 2',
                'crop_type': 'Tomatoes',
                'planting_date': today - timedelta(days=15),
                'current_stage': Field.Stage.PLANTED,
                'assigned_agent': agent1,
            },
            {
                'name': 'Greenhouse Row 1',
                'crop_type': 'Peppers',
                'planting_date': today - timedelta(days=45),
                'current_stage': Field.Stage.READY,
                'assigned_agent': agent2,
            },
            # Completed fields
            {
                'name': 'South Valley',
                'crop_type': 'Wheat',
                'planting_date': today - timedelta(days=120),
                'current_stage': Field.Stage.HARVESTED,
                'assigned_agent': agent2,
            },
            {
                'name': 'River Bend Field',
                'crop_type': 'Soybeans',
                'planting_date': today - timedelta(days=140),
                'current_stage': Field.Stage.HARVESTED,
                'assigned_agent': agent1,
            },
            # At-risk fields (old planting dates, still early stage)
            {
                'name': 'West Pasture',
                'crop_type': 'Sorghum',
                'planting_date': today - timedelta(days=100),
                'current_stage': Field.Stage.PLANTED,
                'assigned_agent': agent2,
            },
            {
                'name': 'Hilltop Block',
                'crop_type': 'Sunflower',
                'planting_date': today - timedelta(days=95),
                'current_stage': Field.Stage.GROWING,
                'assigned_agent': agent1,
            },
            {
                'name': 'Irrigation Zone 3',
                'crop_type': 'Beans',
                'planting_date': today - timedelta(days=60),
                'current_stage': Field.Stage.GROWING,
                'assigned_agent': agent2,
            },
        ]

        for data in seed_fields:
            field, created = Field.objects.get_or_create(
                name=data['name'],
                defaults=data,
            )
            if not created:
                for k, v in data.items():
                    setattr(field, k, v)
                field.save()

        # Updates are created separately so audit history remains explicit and reproducible.
        updates = [
            ('North Plot A', agent1, Field.Stage.PLANTED, Field.Stage.GROWING,
             'Good germination, soil moisture adequate. Pest control applied.', 20),
            ('East Block 2', agent1, Field.Stage.PLANTED, Field.Stage.PLANTED,
             'Seeds planted. Irrigation system checked and functional.', 14),
            ('Greenhouse Row 1', agent2, Field.Stage.GROWING, Field.Stage.READY,
             'Plants at full maturity. Harvest crew scheduled for next week.', 5),
            ('South Valley', agent2, Field.Stage.READY, Field.Stage.HARVESTED,
             'Harvest complete. Yield approximately 4.2 tonnes per acre.', 10),
            ('River Bend Field', agent1, Field.Stage.READY, Field.Stage.HARVESTED,
             'Excellent harvest season. Storage arranged.', 15),
            ('West Pasture', agent2, Field.Stage.PLANTED, Field.Stage.PLANTED,
             'Slow germination due to low rainfall. Monitoring closely.', 30),
        ]

        for field_name, agent, prev, new, notes, days_ago in updates:
            try:
                field = Field.objects.get(name=field_name)
                FieldUpdate.objects.get_or_create(
                    field=field,
                    notes=notes,
                    defaults={
                        'updated_by': agent,
                        'previous_stage': prev,
                        'new_stage': new,
                        'created_at': timezone.now() - timedelta(days=days_ago),
                    }
                )
            except Field.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS(
            '\n✅ Seed data created!\n'
            '  Admin:   admin / admin1234\n'
            '  Agent 1: agent_james / agent1234\n'
            '  Agent 2: agent_wanjiru / agent1234\n'
        ))

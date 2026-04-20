"""Test coverage for field status logic, services, permissions, and summaries."""

from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from fields.models import Field, FieldUpdate
from fields.services import create_field_update, get_admin_summary, get_agent_summary


class FieldStatusLogicTest(TestCase):
    """Verifies the derived field status and progress calculations."""

    def setUp(self):
        self.agent = User.objects.create_user(
            username='testagent', password='pass', role=User.Role.FIELD_AGENT
        )
        self.today = timezone.now().date()

    def make_field(self, stage, days_planted, with_recent_update=False, days_since_update=None):
        field = Field.objects.create(
            name='Test Field',
            crop_type='Maize',
            planting_date=self.today - timedelta(days=days_planted),
            current_stage=stage,
            assigned_agent=self.agent,
        )
        if with_recent_update:
            days = days_since_update if days_since_update is not None else 0
            FieldUpdate.objects.create(
                field=field,
                updated_by=self.agent,
                previous_stage=stage,
                new_stage=stage,
                notes='test',
            )
        return field

    def test_harvested_is_completed(self):
        field = self.make_field(Field.Stage.HARVESTED, 120)
        self.assertEqual(field.computed_status, Field.Status.COMPLETED)

    def test_active_new_planted_field(self):
        field = self.make_field(Field.Stage.PLANTED, 5, with_recent_update=True)
        self.assertEqual(field.computed_status, Field.Status.ACTIVE)

    def test_at_risk_old_planted_field(self):
        field = self.make_field(Field.Stage.PLANTED, 91)
        self.assertEqual(field.computed_status, Field.Status.AT_RISK)

    def test_at_risk_old_growing_field(self):
        field = self.make_field(Field.Stage.GROWING, 95)
        self.assertEqual(field.computed_status, Field.Status.AT_RISK)

    def test_at_risk_no_updates_14_days(self):
        field = self.make_field(Field.Stage.GROWING, 50)
        # No updates created — planting was 50 days ago, should be at risk
        self.assertEqual(field.computed_status, Field.Status.AT_RISK)

    def test_ready_stage_active_if_recent_update(self):
        field = self.make_field(Field.Stage.READY, 70, with_recent_update=True)
        self.assertEqual(field.computed_status, Field.Status.ACTIVE)

    def test_stage_progress(self):
        for stage, expected in [
            (Field.Stage.PLANTED, 25),
            (Field.Stage.GROWING, 50),
            (Field.Stage.READY, 75),
            (Field.Stage.HARVESTED, 100),
        ]:
            field = self.make_field(stage, 10)
            self.assertEqual(field.stage_progress, expected)


class FieldUpdateServiceTest(TestCase):
    """Verifies that the shared update service writes audit records correctly."""

    def setUp(self):
        self.agent = User.objects.create_user(
            username='agent', password='pass', role=User.Role.FIELD_AGENT
        )
        self.field = Field.objects.create(
            name='Service Test Field',
            crop_type='Wheat',
            planting_date=timezone.now().date() - timedelta(days=10),
            current_stage=Field.Stage.PLANTED,
            assigned_agent=self.agent,
        )

    def test_create_field_update_changes_stage(self):
        update = create_field_update(self.field, self.agent, Field.Stage.GROWING, 'Growing well')
        self.field.refresh_from_db()
        self.assertEqual(self.field.current_stage, Field.Stage.GROWING)
        self.assertEqual(update.previous_stage, Field.Stage.PLANTED)
        self.assertEqual(update.new_stage, Field.Stage.GROWING)

    def test_field_update_creates_record(self):
        create_field_update(self.field, self.agent, Field.Stage.READY, 'Almost ready')
        self.assertEqual(FieldUpdate.objects.filter(field=self.field).count(), 1)


class PermissionsTest(TestCase):
    """Checks role-based access rules for the HTML field views."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='admin1234', role=User.Role.ADMIN
        )
        self.agent = User.objects.create_user(
            username='agent', password='agent1234', role=User.Role.FIELD_AGENT
        )
        self.other_agent = User.objects.create_user(
            username='other', password='other1234', role=User.Role.FIELD_AGENT
        )
        self.field = Field.objects.create(
            name='Permission Field',
            crop_type='Corn',
            planting_date=timezone.now().date(),
            current_stage=Field.Stage.PLANTED,
            assigned_agent=self.agent,
        )
        self.client = Client()

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get('/fields/')
        self.assertRedirects(response, '/accounts/login/?next=/fields/')

    def test_admin_can_access_field_list(self):
        self.client.login(username='admin', password='admin1234')
        response = self.client.get('/fields/')
        self.assertEqual(response.status_code, 200)

    def test_agent_can_access_field_list(self):
        self.client.login(username='agent', password='agent1234')
        response = self.client.get('/fields/')
        self.assertEqual(response.status_code, 200)

    def test_agent_cannot_access_other_agents_field(self):
        self.client.login(username='other', password='other1234')
        response = self.client.get(f'/fields/{self.field.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_agent_cannot_create_field(self):
        self.client.login(username='agent', password='agent1234')
        response = self.client.get('/fields/create/')
        self.assertEqual(response.status_code, 302)  # redirected away

    def test_admin_can_create_field(self):
        self.client.login(username='admin', password='admin1234')
        response = self.client.get('/fields/create/')
        self.assertEqual(response.status_code, 200)


class SummaryServiceTest(TestCase):
    """Verifies dashboard summary aggregation for admin and agent scopes."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='pass', role=User.Role.ADMIN
        )
        self.agent = User.objects.create_user(
            username='agent', password='pass', role=User.Role.FIELD_AGENT
        )
        today = timezone.now().date()
        Field.objects.create(
            name='F1', crop_type='Maize',
            planting_date=today - timedelta(days=5),
            current_stage=Field.Stage.PLANTED,
            assigned_agent=self.agent,
        )
        Field.objects.create(
            name='F2', crop_type='Wheat',
            planting_date=today - timedelta(days=130),
            current_stage=Field.Stage.HARVESTED,
            assigned_agent=self.agent,
        )

    def test_admin_summary_counts(self):
        summary = get_admin_summary()
        self.assertEqual(summary['total'], 2)
        self.assertIn('active', summary)
        self.assertIn('at_risk', summary)
        self.assertIn('completed', summary)

    def test_agent_summary_only_sees_own_fields(self):
        summary = get_agent_summary(self.agent)
        self.assertEqual(summary['total'], 2)

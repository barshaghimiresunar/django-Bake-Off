from importlib import import_module

from django.apps import apps
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection, connections
from django.test import TransactionTestCase
from django.test.utils import captured_stdout

from .models import Proxy, UserProxy

update_proxy_permissions = import_module(
    "django.contrib.auth.migrations.0011_update_proxy_permissions"
)


class ProxyModelWithDifferentAppLabelTests(TransactionTestCase):
    available_apps = [
        "auth_tests",
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]

    def setUp(self):
        """
        Create proxy permissions with content_type to the concrete model
        rather than the proxy model (as they were before Django 2.2 and
        migration 11).
        """
        Permission.objects.all().delete()
        self.concrete_content_type = ContentType.objects.get_for_model(UserProxy)
        self.default_permission = Permission.objects.create(
            content_type=self.concrete_content_type,
            codename="add_userproxy",
            name="Can add userproxy",
        )
        self.custom_permission = Permission.objects.create(
            content_type=self.concrete_content_type,
            codename="use_different_app_label",
            name="May use a different app label",
        )

    def test_proxy_model_permissions_contenttype(self):
        proxy_model_content_type = ContentType.objects.get_for_model(
            UserProxy, for_concrete_model=False
        )
        self.assertEqual(
            self.default_permission.content_type, self.concrete_content_type
        )
        self.assertEqual(
            self.custom_permission.content_type, self.concrete_content_type
        )
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        self.default_permission.refresh_from_db()
        self.assertEqual(self.default_permission.content_type, proxy_model_content_type)
        self.custom_permission.refresh_from_db()
        self.assertEqual(self.custom_permission.content_type, proxy_model_content_type)

    def test_user_has_now_proxy_model_permissions(self):
        user = User.objects.create()
        user.user_permissions.add(self.default_permission)
        user.user_permissions.add(self.custom_permission)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertTrue(user.has_perm("auth." + permission.codename))
            self.assertFalse(user.has_perm("auth_tests." + permission.codename))
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        # Reload user to purge the _perm_cache.
        user = User._default_manager.get(pk=user.pk)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertFalse(user.has_perm("auth." + permission.codename))
            self.assertTrue(user.has_perm("auth_tests." + permission.codename))

    def test_migrate_backwards(self):
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
            update_proxy_permissions.revert_proxy_model_permissions(apps, editor)
        self.default_permission.refresh_from_db()
        self.assertEqual(
            self.default_permission.content_type, self.concrete_content_type
        )
        self.custom_permission.refresh_from_db()
        self.assertEqual(
            self.custom_permission.content_type, self.concrete_content_type
        )

    def test_user_keeps_same_permissions_after_migrating_backward(self):
        user = User.objects.create()
        user.user_permissions.add(self.default_permission)
        user.user_permissions.add(self.custom_permission)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertTrue(user.has_perm("auth." + permission.codename))
            self.assertFalse(user.has_perm("auth_tests." + permission.codename))
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
            update_proxy_permissions.revert_proxy_model_permissions(apps, editor)
        # Reload user to purge the _perm_cache.
        user = User._default_manager.get(pk=user.pk)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertTrue(user.has_perm("auth." + permission.codename))
            self.assertFalse(user.has_perm("auth_tests." + permission.codename))


class ProxyModelWithSameAppLabelTests(TransactionTestCase):
    available_apps = [
        "auth_tests",
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]

    def setUp(self):
        """
        Create proxy permissions with content_type to the concrete model
        rather than the proxy model (as they were before Django 2.2 and
        migration 11).
        """
        Permission.objects.all().delete()
        self.concrete_content_type = ContentType.objects.get_for_model(Proxy)
        self.default_permission = Permission.objects.create(
            content_type=self.concrete_content_type,
            codename="add_proxy",
            name="Can add proxy",
        )
        self.custom_permission = Permission.objects.create(
            content_type=self.concrete_content_type,
            codename="display_proxys",
            name="May display proxys information",
        )

    def test_proxy_model_permissions_contenttype(self):
        proxy_model_content_type = ContentType.objects.get_for_model(
            Proxy, for_concrete_model=False
        )
        self.assertEqual(
            self.default_permission.content_type, self.concrete_content_type
        )
        self.assertEqual(
            self.custom_permission.content_type, self.concrete_content_type
        )
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        self.default_permission.refresh_from_db()
        self.custom_permission.refresh_from_db()
        self.assertEqual(self.default_permission.content_type, proxy_model_content_type)
        self.assertEqual(self.custom_permission.content_type, proxy_model_content_type)

    def test_user_still_has_proxy_model_permissions(self):
        user = User.objects.create()
        user.user_permissions.add(self.default_permission)
        user.user_permissions.add(self.custom_permission)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertTrue(user.has_perm("auth_tests." + permission.codename))
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        # Reload user to purge the _perm_cache.
        user = User._default_manager.get(pk=user.pk)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertTrue(user.has_perm("auth_tests." + permission.codename))

    def test_migrate_backwards(self):
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
            update_proxy_permissions.revert_proxy_model_permissions(apps, editor)
        self.default_permission.refresh_from_db()
        self.assertEqual(
            self.default_permission.content_type, self.concrete_content_type
        )
        self.custom_permission.refresh_from_db()
        self.assertEqual(
            self.custom_permission.content_type, self.concrete_content_type
        )

    def test_user_keeps_same_permissions_after_migrating_backward(self):
        user = User.objects.create()
        user.user_permissions.add(self.default_permission)
        user.user_permissions.add(self.custom_permission)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertTrue(user.has_perm("auth_tests." + permission.codename))
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
            update_proxy_permissions.revert_proxy_model_permissions(apps, editor)
        # Reload user to purge the _perm_cache.
        user = User._default_manager.get(pk=user.pk)
        for permission in [self.default_permission, self.custom_permission]:
            self.assertTrue(user.has_perm("auth_tests." + permission.codename))

    def test_migrate_with_existing_target_permission(self):
        """
        Permissions may already exist:

        - Old workaround was to manually create permissions for proxy models.
        - Model may have been concrete and then converted to proxy.

        Output a reminder to audit relevant permissions.
        """
        proxy_model_content_type = ContentType.objects.get_for_model(
            Proxy, for_concrete_model=False
        )
        Permission.objects.create(
            content_type=proxy_model_content_type,
            codename="add_proxy",
            name="Can add proxy",
        )
        Permission.objects.create(
            content_type=proxy_model_content_type,
            codename="display_proxys",
            name="May display proxys information",
        )
        with captured_stdout() as stdout:
            with connection.schema_editor() as editor:
                update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        self.assertIn(
            "A problem arose migrating proxy model permissions", stdout.getvalue()
        )


class MultiDBProxyModelAppLabelTests(TransactionTestCase):
    databases = {"default", "other"}
    available_apps = [
        "auth_tests",
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]

    def setUp(self):
        ContentType.objects.all().delete()
        Permission.objects.using("other").delete()
        concrete_content_type = ContentType.objects.db_manager("other").get_for_model(
            Proxy
        )
        self.permission = Permission.objects.using("other").create(
            content_type=concrete_content_type,
            codename="add_proxy",
            name="Can add proxy",
        )

    def test_migrate_other_database(self):
        proxy_model_content_type = ContentType.objects.db_manager(
            "other"
        ).get_for_model(Proxy, for_concrete_model=False)
        with connections["other"].schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        self.permission.refresh_from_db()
        self.assertEqual(self.permission.content_type, proxy_model_content_type)


class ProxyModelDuplicatePermissionsIdempotencyTests(TransactionTestCase):
    available_apps = [
        "auth_tests",
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]

    def test_idempotent_with_existing_target_permissions(self):
        """
        If target proxy permissions already exist (e.g., manual creation or a
        proxy recreated after a rename), migrating should succeed without
        creating additional duplicates and should be safe to run multiple times.
        """
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        # Start from a clean state for this scenario.
        Permission.objects.all().delete()

        proxy_ct = ContentType.objects.get_for_model(Proxy, for_concrete_model=False)
        concrete_ct = ContentType.objects.get_for_model(Proxy)

        # Pre-create the target (proxy) permissions as might exist in real
        # projects due to manual workarounds or model renames.
        Permission.objects.create(
            content_type=proxy_ct,
            codename="add_proxy",
            name="Can add proxy",
        )
        Permission.objects.create(
            content_type=proxy_ct,
            codename="display_proxys",
            name="May display proxys information",
        )

        # Also create the historical (concrete) permissions that Django's
        # migration updates.
        Permission.objects.create(
            content_type=concrete_ct,
            codename="add_proxy",
            name="Can add proxy",
        )
        Permission.objects.create(
            content_type=concrete_ct,
            codename="display_proxys",
            name="May display proxys information",
        )

        # Run the migration twice to assert idempotency and absence of
        # IntegrityError even when target rows already exist.
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)

        # Exactly one proxy permission per codename; no extra duplicates created.
        for codename in ["add_proxy", "display_proxys"]:
            self.assertEqual(
                Permission.objects.filter(
                    content_type=proxy_ct, codename=codename
                ).count(),
                1,
            )

    def test_idempotent_without_existing_target_permissions(self):
        """
        When only the historical (concrete) permissions exist, migrating moves
        them to the proxy ContentType and remains safe to re-run with no-op.
        """
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        Permission.objects.all().delete()

        concrete_ct = ContentType.objects.get_for_model(Proxy)
        proxy_ct = ContentType.objects.get_for_model(Proxy, for_concrete_model=False)

        Permission.objects.create(
            content_type=concrete_ct,
            codename="add_proxy",
            name="Can add proxy",
        )
        Permission.objects.create(
            content_type=concrete_ct,
            codename="display_proxys",
            name="May display proxys information",
        )

        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)
        with connection.schema_editor() as editor:
            update_proxy_permissions.update_proxy_model_permissions(apps, editor)

        # After migration, concrete permissions are gone and proxy permissions
        # exist exactly once per codename. Re-running should not change counts.
        for codename in ["add_proxy", "display_proxys"]:
            self.assertEqual(
                Permission.objects.filter(
                    content_type=proxy_ct, codename=codename
                ).count(),
                1,
            )
            self.assertEqual(
                Permission.objects.filter(
                    content_type=concrete_ct, codename=codename
                ).count(),
                0,
            )

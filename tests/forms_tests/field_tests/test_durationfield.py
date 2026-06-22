import datetime

from django.core.exceptions import ValidationError
from django.forms import DurationField
from django.test import SimpleTestCase
from django.utils import translation
from django.utils.duration import duration_string

from . import FormFieldAssertionsMixin


class DurationFieldTest(FormFieldAssertionsMixin, SimpleTestCase):
    def test_durationfield_clean(self):
        f = DurationField()
        self.assertEqual(datetime.timedelta(seconds=30), f.clean("30"))
        self.assertEqual(datetime.timedelta(minutes=15, seconds=30), f.clean("15:30"))
        self.assertEqual(
            datetime.timedelta(hours=1, minutes=15, seconds=30), f.clean("1:15:30")
        )
        self.assertEqual(
            datetime.timedelta(
                days=1, hours=1, minutes=15, seconds=30, milliseconds=300
            ),
            f.clean("1 1:15:30.3"),
        )
        self.assertEqual(
            datetime.timedelta(0, 10800),
            f.clean(datetime.timedelta(0, 10800)),
        )
        msg = "This field is required."
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("")
        msg = "Enter a valid duration."
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("not_a_time")
        with self.assertRaisesMessage(ValidationError, msg):
            DurationField().clean("P3(3D")

    def test_durationfield_clean_not_required(self):
        f = DurationField(required=False)
        self.assertIsNone(f.clean(""))

    def test_overflow(self):
        msg = "The number of days must be between {min_days} and {max_days}.".format(
            min_days=datetime.timedelta.min.days,
            max_days=datetime.timedelta.max.days,
        )
        f = DurationField()
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("1000000000 00:00:00")
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("-1000000000 00:00:00")

    def test_overflow_translation(self):
        msg = "Le nombre de jours doit être entre {min_days} et {max_days}.".format(
            min_days=datetime.timedelta.min.days,
            max_days=datetime.timedelta.max.days,
        )
        with translation.override("fr"):
            with self.assertRaisesMessage(ValidationError, msg):
                DurationField().clean("1000000000 00:00:00")

    def test_durationfield_render(self):
        self.assertWidgetRendersTo(
            DurationField(initial=datetime.timedelta(hours=1)),
            '<input id="id_f" type="text" name="f" value="01:00:00" required>',
        )

    def test_durationfield_integer_value(self):
        f = DurationField()
        self.assertEqual(datetime.timedelta(0, 10800), f.clean(10800))

    def test_durationfield_prepare_value(self):
        field = DurationField()
        td = datetime.timedelta(minutes=15, seconds=30)
        self.assertEqual(field.prepare_value(td), duration_string(td))
        self.assertEqual(field.prepare_value("arbitrary"), "arbitrary")
        self.assertIsNone(field.prepare_value(None))


class DurationFieldMessageFormatTests(SimpleTestCase):
    def test_invalid_message_shows_expected_format(self):
        f = DurationField()
        msg = "Enter a valid duration in the format [DD] [[HH:]MM:]ss[.uuuuuu]."
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("14:")  # Missing mandatory seconds.

    def test_valid_examples_from_spec(self):
        f = DurationField()
        # "14:00" -> 14 minutes, 0 seconds
        self.assertEqual(f.clean("14:00"), datetime.timedelta(minutes=14))
        # "62" -> 62 seconds
        self.assertEqual(f.clean("62"), datetime.timedelta(seconds=62))
        # "3 1:02:03" -> 3 days, 1 hour, 2 minutes, 3 seconds
        self.assertEqual(
            f.clean("3 1:02:03"),
            datetime.timedelta(days=3, hours=1, minutes=2, seconds=3),
        )


class DurationFieldAdditionalFormatTests(SimpleTestCase):
    def test_invalid_message_hours_without_seconds(self):
        f = DurationField()
        msg = "Enter a valid duration in the format [DD] [[HH:]MM:]ss[.uuuuuu]."
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("1:")  # Missing mandatory seconds.

    def test_invalid_message_too_many_parts(self):
        f = DurationField()
        msg = "Enter a valid duration in the format [DD] [[HH:]MM:]ss[.uuuuuu]."
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("1:2:3:4")  # Four colon-separated parts are invalid.

    def test_microseconds_parsing(self):
        f = DurationField()
        self.assertEqual(
            f.clean("00:00:01.123456"),
            datetime.timedelta(seconds=1, microseconds=123456),
        )

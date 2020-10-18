import json
import io

import pandas as pd

from django.test import TestCase, mock

from .. import models


class TestFailedTaskModel(TestCase):
    def test_instantiate_task_converts_args_to_str(self):
        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[1, 2],
            kwargs={},
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        self.assertEqual(task.args, json.dumps([1, 2]))

    def test_instantiate_task_converts_kwargs_to_str(self):
        kwargs = {"a": 1, "b": 2}
        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs=kwargs,
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        self.assertEqual(task.kwargs, json.dumps(kwargs, sort_keys=True))

    def test_false_args_kwargs_initialised_as_none(self):
        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs={},
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        self.assertIsNone(task.args)
        self.assertIsNone(task.kwargs)

    def test_instantiate_supports_dataframes_in_kwargs_and_args(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 4, 5]})
        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[df],
            kwargs={"count_records": df},
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )

        handle = io.StringIO()
        df.to_json(handle, orient="records")
        handle.seek(0)
        expected = handle.read()

        self.assertEqual(task.args, json.dumps([expected]))
        self.assertEqual(
            task.kwargs,
            json.dumps({"count_records": expected}, sort_keys=True),
        )

    def test_update_or_create_creates_new_task(self):
        task, created = models.FailedTask.update_or_create(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs={},
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        self.assertTrue(created)
        self.assertEqual(task.failures, 1)

    def test_update_or_create_creates_updates_existing_task(self):
        models.FailedTask.update_or_create(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs={},
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )

        # Creates the task twice, updating the original.
        task, created = models.FailedTask.update_or_create(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs={},
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        self.assertFalse(created)
        self.assertEqual(task.failures, 2)

    @mock.patch("core.tasks.add.submit_task")
    def test_can_retry_task(self, patch):
        kwargs = {"a": 1, "b": 2}
        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs=kwargs,
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        task.save()

        task.retry_and_delete()
        patch.assert_called()
        self.assertEqual(patch.call_args[1], {"args": (), "kwargs": kwargs})
        self.assertEqual(models.FailedTask.objects.count(), 0)

    def test_inline_retry_does_not_delete_if_failure(self):
        kwargs = {"a": 1, "b": "1"}  # type error
        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs=kwargs,
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        task.save()

        with self.assertRaises(TypeError):
            task.retry_and_delete(inline=True)
            self.assertEqual(models.FailedTask.objects.count(), 1)

    def test_can_find_existing_task(self):
        kwargs = {"a": 1, "b": 2}
        existing = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs=kwargs,
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        existing.save()

        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[],
            kwargs=kwargs,
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        self.assertEqual(task.find_existing(), existing)

    def test_can_find_existing_task_when_kwargs_has_df(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 4, 5]})
        kwargs = {"a": 1, "b": 2, "df": df}
        existing = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[df],
            kwargs=kwargs,
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        existing.save()

        task = models.FailedTask.instantiate_task(
            name="add",
            full_name="core.tasks.add",
            args=[df],
            kwargs=kwargs,
            exc=Exception("This is a test"),
            traceback=None,
            task_id="1",
            user=None,
        )
        self.assertEqual(task.find_existing(), existing)

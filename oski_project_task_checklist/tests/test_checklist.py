from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOskiTaskChecklist(TransactionCase):
    """Vérifie le calcul de progression et le comportement de la checklist."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {"name": "Projet Test Checklist Oski"}
        )
        cls.task = cls.env["project.task"].create(
            {"name": "Tâche Test Checklist Oski", "project_id": cls.project.id}
        )

    def _add_item(self, name, done=False, sequence=10):
        return self.env["oski.task.checklist.item"].create(
            {
                "task_id": self.task.id,
                "name": name,
                "done": done,
                "sequence": sequence,
            }
        )

    def test_progress_zero_without_items(self):
        """Une tâche sans items affiche 0 % d'avancement."""
        self.assertEqual(self.task.oski_checklist_progress, 0.0)
        self.assertEqual(self.task.oski_checklist_count, 0)

    def test_progress_half_then_full(self):
        """4 items dont 2 faits → 50 % ; tous faits → 100 %."""
        self._add_item("Étape 1", done=True)
        self._add_item("Étape 2", done=True)
        item3 = self._add_item("Étape 3", done=False)
        item4 = self._add_item("Étape 4", done=False)

        self.assertEqual(self.task.oski_checklist_progress, 50.0)

        (item3 | item4).write({"done": True})
        self.assertEqual(self.task.oski_checklist_progress, 100.0)

    def test_cascade_delete(self):
        """Supprimer la tâche supprime ses items (ondelete cascade)."""
        self._add_item("Étape A")
        self._add_item("Étape B")
        item_ids = self.task.oski_checklist_ids.ids
        self.assertTrue(item_ids)

        self.task.unlink()

        remaining = self.env["oski.task.checklist.item"].search(
            [("id", "in", item_ids)]
        )
        self.assertFalse(remaining)

    def test_count(self):
        """Le compteur d'items reflète le nombre réel d'items."""
        self._add_item("Étape 1")
        self._add_item("Étape 2")
        self._add_item("Étape 3")
        self.assertEqual(self.task.oski_checklist_count, 3)

from django.test import TestCase
from django.db import IntegrityError
from catalog.models import GemstoneSpecies, GemstoneVariety


class GemstoneSpeciesModelTest(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum",
            common_name="Sapphire & Ruby",
            code="COR",
            description="Aluminium oxide mineral.",
        )

    def test_str(self):
        self.assertEqual(str(self.species), "Corundum")

    def test_name_is_unique(self):
        with self.assertRaises(IntegrityError):
            GemstoneSpecies.objects.create(
                name="Corundum",
                common_name="Duplicate",
                code="DUP",
            )

    def test_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            GemstoneSpecies.objects.create(
                name="Other",
                common_name="Other",
                code="COR",
            )

    def test_is_active_defaults_true(self):
        self.assertTrue(self.species.is_active)

    def test_created_at_set_on_create(self):
        self.assertIsNotNone(self.species.created_at)

    def test_updated_at_changes_on_save(self):
        original = self.species.updated_at
        self.species.description = "Updated"
        self.species.save()
        self.assertGreaterEqual(self.species.updated_at, original)


class GemstoneVarietyModelTest(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum",
            common_name="Sapphire & Ruby",
            code="COR",
        )
        self.variety = GemstoneVariety.objects.create(
            species=self.species,
            name="Blue Sapphire",
            code="BSAP",
            typical_colors="Pale blue to deep royal blue",
        )

    def test_str(self):
        self.assertEqual(str(self.variety), "Corundum — Blue Sapphire")

    def test_is_active_defaults_true(self):
        self.assertTrue(self.variety.is_active)

    def test_duplicate_name_within_same_species_raises(self):
        with self.assertRaises(IntegrityError):
            GemstoneVariety.objects.create(
                species=self.species,
                name="Blue Sapphire",
                code="BSAP2",
            )

    def test_duplicate_code_within_same_species_raises(self):
        with self.assertRaises(IntegrityError):
            GemstoneVariety.objects.create(
                species=self.species,
                name="Another Sapphire",
                code="BSAP",
            )

    def test_same_name_allowed_across_different_species(self):
        other_species = GemstoneSpecies.objects.create(
            name="Spinel",
            common_name="Spinel",
            code="SPI",
        )
        # Should not raise — same name is allowed across different species
        variety = GemstoneVariety.objects.create(
            species=other_species,
            name="Blue Sapphire",
            code="BSAP",
        )
        self.assertEqual(variety.species, other_species)

    def test_variety_belongs_to_species(self):
        self.assertEqual(self.variety.species, self.species)

    def test_species_varieties_reverse_relation(self):
        self.assertIn(self.variety, self.species.varieties.all())

    def test_deleting_species_is_protected(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.species.delete()


class SeedCommandTest(TestCase):

    def test_seed_command_creates_species_and_varieties(self):
        from django.core.management import call_command
        call_command("seed_gemstone_species", verbosity=0)
        self.assertGreater(GemstoneSpecies.objects.count(), 0)
        self.assertGreater(GemstoneVariety.objects.count(), 0)

    def test_seed_command_is_idempotent(self):
        from django.core.management import call_command
        call_command("seed_gemstone_species", verbosity=0)
        count_species = GemstoneSpecies.objects.count()
        count_varieties = GemstoneVariety.objects.count()
        # Run again — should not create duplicates
        call_command("seed_gemstone_species", verbosity=0)
        self.assertEqual(GemstoneSpecies.objects.count(), count_species)
        self.assertEqual(GemstoneVariety.objects.count(), count_varieties)

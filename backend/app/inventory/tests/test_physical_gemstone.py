from django.test import TestCase
from django.utils import timezone
from inventory.models import (
    PhysicalGemstone,
    GemstoneIDSequence,
    GemstoneLifecycleState,
    LIFECYCLE_TRANSITIONS,
)
from catalog.models import GemstoneSpecies, GemstoneVariety


class PhysicalGemstoneSetup(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum", common_name="Sapphire & Ruby", code="COR"
        )
        self.variety = GemstoneVariety.objects.create(
            species=self.species,
            name="Blue Sapphire",
            code="BSAP",
        )

    def make_gemstone(self, **kwargs):
        defaults = {
            "species": self.species,
            "variety": self.variety,
            "acquisition_date": timezone.now().date(),
        }
        defaults.update(kwargs)
        return PhysicalGemstone.objects.create(**defaults)


class GemstoneIDGenerationTest(PhysicalGemstoneSetup):

    def test_id_is_generated_on_create(self):
        gem = self.make_gemstone()
        self.assertIsNotNone(gem.gemstone_id)
        self.assertNotEqual(gem.gemstone_id, "")

    def test_id_format(self):
        gem = self.make_gemstone()
        year = timezone.now().year
        self.assertTrue(gem.gemstone_id.startswith(f"CEY-COR-{year}-"))

    def test_id_sequence_is_zero_padded_to_six_digits(self):
        gem = self.make_gemstone()
        sequence_part = gem.gemstone_id.split("-")[-1]
        self.assertEqual(len(sequence_part), 6)

    def test_sequential_ids_are_unique(self):
        gem1 = self.make_gemstone()
        gem2 = self.make_gemstone()
        self.assertNotEqual(gem1.gemstone_id, gem2.gemstone_id)

    def test_sequence_increments(self):
        gem1 = self.make_gemstone()
        gem2 = self.make_gemstone()
        seq1 = int(gem1.gemstone_id.split("-")[-1])
        seq2 = int(gem2.gemstone_id.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_id_is_immutable_after_creation(self):
        gem = self.make_gemstone()
        original_id = gem.gemstone_id
        gem.acquisition_notes = "Updated notes"
        gem.save()
        gem.refresh_from_db()
        self.assertEqual(gem.gemstone_id, original_id)

    def test_different_species_have_independent_sequences(self):
        spinel = GemstoneSpecies.objects.create(
            name="Spinel", common_name="Spinel", code="SPI"
        )
        gem_cor = self.make_gemstone()
        gem_spi = self.make_gemstone(species=spinel, variety=None)
        year = timezone.now().year
        self.assertTrue(gem_cor.gemstone_id.startswith(f"CEY-COR-{year}-"))
        self.assertTrue(gem_spi.gemstone_id.startswith(f"CEY-SPI-{year}-"))
        # Both should be sequence 000001 since they are independent
        self.assertEqual(gem_cor.gemstone_id.split("-")[-1], "000001")
        self.assertEqual(gem_spi.gemstone_id.split("-")[-1], "000001")

    def test_id_sequence_record_is_created(self):
        year = timezone.now().year
        self.make_gemstone()
        self.assertTrue(
            GemstoneIDSequence.objects.filter(
                species_code="COR", year=year
            ).exists()
        )


class GemstoneLifecycleTest(PhysicalGemstoneSetup):

    def test_default_state_is_acquired(self):
        gem = self.make_gemstone()
        self.assertEqual(gem.lifecycle_state, GemstoneLifecycleState.ACQUIRED)

    def test_valid_transition_acquired_to_tested(self):
        gem = self.make_gemstone()
        gem.transition_to(GemstoneLifecycleState.TESTED)
        gem.refresh_from_db()
        self.assertEqual(gem.lifecycle_state, GemstoneLifecycleState.TESTED)

    def test_valid_transition_acquired_to_stored(self):
        gem = self.make_gemstone()
        gem.transition_to(GemstoneLifecycleState.STORED)
        gem.refresh_from_db()
        self.assertEqual(gem.lifecycle_state, GemstoneLifecycleState.STORED)

    def test_invalid_transition_raises_value_error(self):
        gem = self.make_gemstone()
        with self.assertRaises(ValueError):
            gem.transition_to(GemstoneLifecycleState.SOLD)

    def test_invalid_transition_acquired_to_delivered_raises(self):
        gem = self.make_gemstone()
        with self.assertRaises(ValueError):
            gem.transition_to(GemstoneLifecycleState.DELIVERED)

    def test_delivered_state_has_no_further_transitions(self):
        self.assertEqual(LIFECYCLE_TRANSITIONS[GemstoneLifecycleState.DELIVERED], [])

    def test_full_lifecycle_path(self):
        gem = self.make_gemstone()
        path = [
            GemstoneLifecycleState.TESTED,
            GemstoneLifecycleState.CERTIFIED,
            GemstoneLifecycleState.PHOTOGRAPHED,
            GemstoneLifecycleState.STORED,
            GemstoneLifecycleState.LISTED,
            GemstoneLifecycleState.RESERVED,
            GemstoneLifecycleState.SOLD,
            GemstoneLifecycleState.EXPORTED,
            GemstoneLifecycleState.DELIVERED,
        ]
        for state in path:
            gem.transition_to(state)
        gem.refresh_from_db()
        self.assertEqual(gem.lifecycle_state, GemstoneLifecycleState.DELIVERED)

    def test_transition_persists_to_database(self):
        gem = self.make_gemstone()
        gem.transition_to(GemstoneLifecycleState.TESTED)
        gem_from_db = PhysicalGemstone.objects.get(pk=gem.pk)
        self.assertEqual(gem_from_db.lifecycle_state, GemstoneLifecycleState.TESTED)


class GemstoneModelTest(PhysicalGemstoneSetup):

    def test_str_returns_gemstone_id(self):
        gem = self.make_gemstone()
        self.assertEqual(str(gem), gem.gemstone_id)

    def test_variety_is_optional(self):
        gem = self.make_gemstone(variety=None)
        self.assertIsNone(gem.variety)
        self.assertIsNotNone(gem.gemstone_id)

    def test_deleting_species_is_protected(self):
        from django.db.models import ProtectedError
        self.make_gemstone()
        with self.assertRaises(ProtectedError):
            self.species.delete()

    def test_created_at_is_set(self):
        gem = self.make_gemstone()
        self.assertIsNotNone(gem.created_at)

    def test_updated_at_changes_on_save(self):
        gem = self.make_gemstone()
        original = gem.updated_at
        gem.internal_notes = "Updated"
        gem.save()
        self.assertGreaterEqual(gem.updated_at, original)

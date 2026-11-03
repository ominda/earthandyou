from django.test import TestCase
from django.db import IntegrityError
from catalog.models import (
    GemstoneSpecies,
    GemstoneAttributeDefinition,
    GemstoneAttributeOption,
    AttributeDataType,
)


class GemstoneAttributeDefinitionModelTest(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum", common_name="Sapphire & Ruby", code="COR"
        )
        self.attr = GemstoneAttributeDefinition.objects.create(
            species=self.species,
            name="Primary Color",
            key="primary_color",
            data_type=AttributeDataType.SELECT,
            is_required=True,
            is_filterable=True,
            display_order=1,
        )

    def test_str(self):
        self.assertEqual(str(self.attr), "Corundum — Primary Color")

    def test_defaults(self):
        attr = GemstoneAttributeDefinition.objects.create(
            species=self.species,
            name="Notes",
            key="notes",
        )
        self.assertEqual(attr.data_type, AttributeDataType.TEXT)
        self.assertFalse(attr.is_required)
        self.assertFalse(attr.is_filterable)
        self.assertTrue(attr.is_displayed)
        self.assertEqual(attr.display_order, 0)

    def test_duplicate_key_within_same_species_raises(self):
        with self.assertRaises(IntegrityError):
            GemstoneAttributeDefinition.objects.create(
                species=self.species,
                name="Color Duplicate",
                key="primary_color",
            )

    def test_same_key_allowed_across_different_species(self):
        other = GemstoneSpecies.objects.create(
            name="Spinel", common_name="Spinel", code="SPI"
        )
        attr = GemstoneAttributeDefinition.objects.create(
            species=other,
            name="Primary Color",
            key="primary_color",
            data_type=AttributeDataType.SELECT,
        )
        self.assertEqual(attr.species, other)

    def test_deleting_species_is_protected(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.species.delete()

    def test_reverse_relation_from_species(self):
        self.assertIn(self.attr, self.species.attribute_definitions.all())


class GemstoneAttributeOptionModelTest(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum", common_name="Sapphire & Ruby", code="COR"
        )
        self.attr = GemstoneAttributeDefinition.objects.create(
            species=self.species,
            name="Shape",
            key="shape",
            data_type=AttributeDataType.SELECT,
        )
        self.option = GemstoneAttributeOption.objects.create(
            attribute=self.attr,
            value="Oval",
            display_order=1,
        )

    def test_str(self):
        self.assertEqual(str(self.option), "Shape: Oval")

    def test_duplicate_value_within_same_attribute_raises(self):
        with self.assertRaises(IntegrityError):
            GemstoneAttributeOption.objects.create(
                attribute=self.attr,
                value="Oval",
            )

    def test_same_value_allowed_across_different_attributes(self):
        other_attr = GemstoneAttributeDefinition.objects.create(
            species=self.species,
            name="Cut Style",
            key="cut_style",
            data_type=AttributeDataType.SELECT,
        )
        option = GemstoneAttributeOption.objects.create(
            attribute=other_attr,
            value="Oval",
        )
        self.assertEqual(option.attribute, other_attr)

    def test_options_deleted_when_attribute_deleted(self):
        attr_id = self.attr.id
        self.attr.delete()
        self.assertFalse(
            GemstoneAttributeOption.objects.filter(attribute_id=attr_id).exists()
        )

    def test_reverse_relation_from_attribute(self):
        self.assertIn(self.option, self.attr.options.all())


class SeedAttributeDefinitionsCommandTest(TestCase):

    def setUp(self):
        from django.core.management import call_command
        call_command("seed_gemstone_species", verbosity=0)

    def test_seed_creates_definitions_and_options(self):
        from django.core.management import call_command
        call_command("seed_attribute_definitions", verbosity=0)
        self.assertGreater(GemstoneAttributeDefinition.objects.count(), 0)
        self.assertGreater(GemstoneAttributeOption.objects.count(), 0)

    def test_seed_is_idempotent(self):
        from django.core.management import call_command
        call_command("seed_attribute_definitions", verbosity=0)
        count_defs = GemstoneAttributeDefinition.objects.count()
        count_opts = GemstoneAttributeOption.objects.count()
        call_command("seed_attribute_definitions", verbosity=0)
        self.assertEqual(GemstoneAttributeDefinition.objects.count(), count_defs)
        self.assertEqual(GemstoneAttributeOption.objects.count(), count_opts)

    def test_common_attributes_exist_for_all_species(self):
        from django.core.management import call_command
        from catalog.models import GemstoneSpecies
        call_command("seed_attribute_definitions", verbosity=0)
        for species in GemstoneSpecies.objects.all():
            self.assertTrue(
                species.attribute_definitions.filter(key="carat_weight").exists(),
                f"carat_weight missing for {species.name}",
            )
            self.assertTrue(
                species.attribute_definitions.filter(key="shape").exists(),
                f"shape missing for {species.name}",
            )

    def test_species_specific_attributes_exist(self):
        from django.core.management import call_command
        call_command("seed_attribute_definitions", verbosity=0)
        corundum = GemstoneSpecies.objects.get(code="COR")
        self.assertTrue(corundum.attribute_definitions.filter(key="asterism").exists())
        chrysoberyl = GemstoneSpecies.objects.get(code="CHR")
        self.assertTrue(chrysoberyl.attribute_definitions.filter(key="chatoyancy").exists())

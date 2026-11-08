from dataclasses import replace
import unittest
from heating_model import Heating, VARIANTS
from storage_model import Storage, SIZES, compare_storage, validate_storage, comparison_rows
from model import Assumptions


class StorageTests(unittest.TestCase):
    def test_costs_and_delta(self):
        a, s = Assumptions(years=2), Storage(discount=3000., upgrade14=2000., size=14)
        h = Heating(capacity=13.8, charge_power=7., discharge_power=7.)
        r = compare_storage(h, VARIANTS[0], a, 0, s)
        self.assertEqual(r["with_investment"], 20090.)
        self.assertEqual(r["without_investment"], 15090.)
        self.assertEqual(r["extra_investment"], 5000.)
        self.assertAlmostEqual(r["delta"][0]["balance"], -5000.)
        self.assertAlmostEqual(r["npv"], -5000.+sum(x["net"]/1.03**x["year"] for x in r["delta"][1:]))
        cheaper = compare_storage(h, VARIANTS[0], a, 0, replace(s, discount=1000.))
        self.assertAlmostEqual(cheaper["npv"]-r["npv"], 2000.)
        self.assertAlmostEqual(cheaper["first_benefit"], r["first_benefit"])

    def test_shared_vs_extra_replacement(self):
        a, h = Assumptions(years=2, replacement_year=2), Heating()
        base = compare_storage(h, VARIANTS[0], a, 0, Storage())
        changed = compare_storage(h, VARIANTS[0], replace(a, replacement_cost=9000.), 0, Storage())
        self.assertAlmostEqual(base["npv"], changed["npv"])
        extra = compare_storage(h, VARIANTS[0], a, 0, Storage(replacement_extra=1000., replacement_year=2))
        self.assertAlmostEqual(base["npv"]-extra["npv"], 1000/1.03**2)

    def test_classes_and_invalid_discount(self):
        self.assertEqual([SIZES[k][0] for k in (7,14,21)], [6.9,13.8,20.7])
        with self.assertRaises(ValueError):
            validate_storage(Storage(discount=20000.), Assumptions())

    def test_difference_row_reconciles(self):
        comp = compare_storage(Heating(capacity=20.7, charge_power=10., discharge_power=10.),
                               VARIANTS[0], Assumptions(), 30., Storage(size=21))
        rows = comparison_rows(comp)
        self.assertEqual(len(rows), 3)
        for key in ("investment", "annual_net", "npv"):
            self.assertAlmostEqual(rows[2][key], rows[0][key]-rows[1][key])
        self.assertIsNone(rows[2]["payback"])
        self.assertAlmostEqual(rows[2]["npv"], 1448.5, delta=1.)


if __name__ == "__main__":
    unittest.main()

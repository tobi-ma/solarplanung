from dataclasses import replace
from pathlib import Path
import unittest
from model import Assumptions, calculate, sustained_payback


class ModelTests(unittest.TestCase):
    def test_energy_and_first_year(self):
        a = Assumptions()
        r = calculate(a, 0, 55)
        f = r["first"]
        self.assertAlmostEqual(f["own"], 3883)
        self.assertAlmostEqual(f["losses"], 353)
        self.assertAlmostEqual(f["export"], 2824)
        self.assertAlmostEqual(f["net"], 3883 * .306 + 2824 * .077 - 150)
        for row in r["rows"][1:]:
            self.assertAlmostEqual(row["generation"], row["own"] + row["losses"] + row["export"])

    def test_replacement_degradation_and_discount(self):
        a = Assumptions()
        r = calculate(a, 10, 40)
        self.assertAlmostEqual(r["first"]["generation"], 6354)
        self.assertEqual(r["rows"][13]["replacement"], 4000)
        self.assertAlmostEqual(r["rows"][2]["generation"], 6354 * .996)
        self.assertAlmostEqual(r["npv"], -18090 + sum(x["net"] / 1.03 ** x["year"] for x in r["rows"][1:]))

    def test_no_revenue_and_invalid_energy(self):
        self.assertIsNone(calculate(replace(Assumptions(), generation=0), 0, 55)["payback"])
        with self.assertRaises(ValueError):
            calculate(Assumptions(), 0, 96)
        with self.assertRaises(ValueError):
            calculate(Assumptions(), -1, 55)

    def test_tariff_ends(self):
        r = calculate(replace(Assumptions(), feed_years=1), 0, 40)
        self.assertGreater(r["rows"][1]["feed"], 0)
        self.assertEqual(r["rows"][2]["feed"], 0)

    def test_recrossing_and_monotonicity(self):
        rows = [dict(year=i, b=v) for i, v in enumerate([-10, 5, -5, 5])]
        self.assertAlmostEqual(sustained_payback(rows, "b"), 2.5)
        for own in (40, 55, 70):
            values = [calculate(Assumptions(), shade, own)["npv"] for shade in (0, 10, 20, 30)]
            self.assertEqual(values, sorted(values, reverse=True))


class UITests(unittest.TestCase):
    def test_interaction(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name("app.py"))).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertIn("18.090", app.metric[0].value)
        self.assertIn("Heizung & Speicher", [tab.label for tab in app.tabs])
        self.assertEqual(app.number_input(key="h_heat").value, 16000.)
        app.number_input(key="scaffold").set_value(0.).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("16.090", app.metric[0].value)
        app.number_input(key="share_2").set_value(99.).run()
        self.assertGreater(len(app.error), 0)

    def test_heating_controls(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name("app.py"))).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        app.checkbox(key="h_battery").uncheck()
        app.checkbox(key="h_central_cooling").check().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.session_state["h_battery"])
        self.assertEqual(len(app.warning), 0)

    def test_storage_size_and_price_controls(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name("app.py"))).run(timeout=30)
        app.selectbox(key="b_size").select(14).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.number_input(key="h_capacity").value, 13.8)
        self.assertEqual(app.number_input(key="h_charge_power").value, 7.)
        app.number_input(key="b_discount").set_value(3000.)
        app.number_input(key="b_upgrade14").set_value(2000.).run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["b_discount"], 3000.)


if __name__ == "__main__":
    unittest.main()

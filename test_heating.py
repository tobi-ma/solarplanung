from dataclasses import replace
import unittest
from heating_model import Heating, VARIANTS, simulate, profiles, weather, financial
from model import Assumptions


class HeatingTests(unittest.TestCase):
    def test_weather_and_annual_loads(self):
        self.assertEqual(len(weather()), 8760)
        h = Heating(central_cooling=True)
        for variant in VARIANTS:
            sim = simulate(h, variant, detail=True)
            t = sim["totals"]
            self.assertAlmostEqual(t["pv"], 7060, places=5)
            self.assertAlmostEqual(t["household"], 3500, places=5)
            self.assertAlmostEqual(t["dhw"], 1000, places=5)
            self.assertAlmostEqual(t["cool"], 250, places=5)
            self.assertAlmostEqual(t["load"], t["grid"]+t["direct"]+t["discharge"], places=5)
            self.assertAlmostEqual(t["pv"], t["direct"]+t["discharge"]+t["loss"]+t["export"]+sim["end_soc"], places=5)
            for r in sim["hourly"]:
                self.assertGreaterEqual(r["soc"], -1e-9)
                self.assertLessEqual(r["soc"], h.capacity+1e-9)
                self.assertLessEqual(r["charge"], h.charge_power+1e-9)
                self.assertLessEqual(r["discharge"], h.discharge_power+1e-9)

    def test_without_battery_and_zero_pv(self):
        h = Heating(battery=False)
        t = simulate(h, VARIANTS[0])["totals"]
        self.assertEqual(t["loss"], 0)
        self.assertEqual(t["charge"], 0)
        sim = simulate(h, VARIANTS[0], generation=0)
        self.assertAlmostEqual(sim["totals"]["grid"], sim["totals"]["load"])

    def test_same_heat_and_cooling_flag(self):
        h = Heating(water_fraction=0)
        s = simulate(h, VARIANTS[0])["totals"]
        c = simulate(h, VARIANTS[1])["totals"]
        self.assertAlmostEqual(s["heat"], h.heat/h.split_jaz)
        self.assertAlmostEqual(c["heat"], h.heat/h.water_jaz)
        self.assertEqual(c["cool"], 0)
        self.assertAlmostEqual(simulate(replace(h, central_cooling=True), VARIANTS[1])["totals"]["cool"], h.cooling/h.seer)

    def test_financial_matches_first_year(self):
        a, h = Assumptions(years=2), Heating()
        t = simulate(h, VARIANTS[0])["totals"]
        fin = financial(h, VARIANTS[0], a, 0)
        expected = (t["direct"]+t["discharge"])*.306 + t["export"]*.077 - 150
        self.assertAlmostEqual(fin["rows"][1]["net"], expected)
        self.assertAlmostEqual(fin["npv"], -a.investment+sum(row["net"]/1.03**row["year"] for row in fin["rows"][1:]))


if __name__ == "__main__":
    unittest.main()

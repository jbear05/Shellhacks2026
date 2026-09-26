"""A realistic, network-free check of the Gridlock ranking model."""

import unittest

from ranking import rank_overlaps


class RankingTest(unittest.TestCase):
    def test_ranks_realistic_gridlock_opportunities(self):
        overlaps = [
            {
                "project_id_a": "06367 A-C, H",
                "utility_a": "Dominion Energy South Carolina",
                "project_id_b": "20277",
                "utility_b": "Georgia Power",
                "project_name_a": "Riverport Tap",
                "project_name_b": "McIntosh - Purrysburg",
                "distance_miles": "12.40",
                "in_service_date_a": "2025-12-31",
                "in_service_date_b": "2026-06-01",
                "start_date_a": "2024-01-01",
                "start_date_b": "2024-01-01",
            },
            {
                "project_id_a": "6809 G",
                "utility_a": "Dominion Energy South Carolina",
                "project_id_b": "17993",
                "utility_b": "Georgia Power",
                "project_name_a": "Stevens Creek - Hooks",
                "project_name_b": "Thomson area transmission work",
                "distance_miles": "21.70",
                "in_service_date_a": "2027-12-31",
                "in_service_date_b": "2030-06-01",
                "start_date_a": "2025-01-01",
                "start_date_b": "2028-01-01",
            },
        ]
        projects = [
            {
                "project_id": "06367 A-C, H",
                "utility": "Dominion Energy South Carolina",
                "project_type": "LINE",
                "voltage_1": "230000",
            },
            {
                "project_id": "20277",
                "utility": "Georgia Power",
                "project_type": "LINE",
                "voltage_1": "230000",
            },
            {
                "project_id": "6809 G",
                "utility": "Dominion Energy South Carolina",
                "project_type": "LINE",
                "voltage_1": "115000",
            },
            {
                "project_id": "17993",
                "utility": "Georgia Power",
                "project_type": "SUBSTATION",
                "voltage_1": "115000",
            },
        ]

        ranked = rank_overlaps(overlaps, projects)

        self.assertEqual([row["rank"] for row in ranked], ["1", "2"])
        self.assertEqual(ranked[0]["project_id_a"], "06367 A-C, H")
        self.assertEqual(ranked[0]["total_score"], "13")
        self.assertEqual(ranked[1]["total_score"], "4")
        self.assertIn("build windows overlap", ranked[0]["ranking_reason"])
        self.assertIn("same voltage", ranked[0]["ranking_reason"])

        print("\nRanked opportunities:")
        for row in ranked:
            print(
                f"{row['rank']}. {row['project_name_a']} + "
                f"{row['project_name_b']} | total={row['total_score']}/15 | "
                f"{row['ranking_reason']}"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
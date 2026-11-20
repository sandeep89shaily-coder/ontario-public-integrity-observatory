import unittest
from src.observatory.corroboration import validate_toronto_report,check_mississauga_threshold,summarize_grants,compare_brampton_arts_dashboard

class CorroborationTests(unittest.TestCase):
    def test_no_false_reconciliation_if_no_source(self):
        self.assertEqual(validate_toronto_report("")["status"],
                         "HOLD_SOURCE_TEXT_MISSING_REQUIRED_VALUES")
    def test_report_arithmetic_needs_source_text(self):
        tokens=("6051950 3,180,416 1,764,477 4,944,893 1,514,477 250,000 "
                "4,382,645 2,618,168 2022 2025")
        x=validate_toronto_report(tokens)
        self.assertEqual(x["status"],"PUBLISHED_AMOUNTS_RECONCILED_NOT_ACTUAL_PAYMENTS")
        self.assertFalse(x["actual_expenditure_verified"])
        self.assertTrue(all(x["calculations"].values()))
    def test_mississauga_threshold_stays_unresolved(self):
        rows=[{"procurement_id":"PRC005493","reported_amount":"$80,000.00",
               "source_url":"https://www.mississauga.ca/test.pdf","source_page":1}]
        x=check_mississauga_threshold(rows,"SECTION 13 SECTION 27 Single Source Information Reports",
              {"https://www.mississauga.ca/test.pdf":"PRC005493 $80,000.00"})
        self.assertTrue(x[0]["published_pdf_amount_and_id_confirmed"])
        self.assertEqual(x[0]["determination"],"UNRESOLVED_ROUTINE_DISCLOSURE_REQUEST")
    def test_2025_grant_aggregate_crosscheck(self):
        grants=[{"year":"2025","approved_amount_as_reported":"$1,750,000",
             "source_url":"https://www.brampton.ca/some.pdf"}]
        x=summarize_grants(grants,[],"$1.75 million and 159",
              "Project Close Out Report and ineligible for future funding")
        self.assertEqual(x["year_2025_official_announcement_cross_check"],"NOT_VERIFIED")
        self.assertFalse(x["by_year"]["2025"]["individual_payments_verified"])

class ArtsDashboardComparisonTests(unittest.TestCase):
    def test_different_measure_not_claimed_as_unspent_money(self):
        rows=[{"year":"2025","program_area_as_reported":"Arts and Culture",
                "approved_amount_as_reported":"$683,744"}]
        x=compare_brampton_arts_dashboard(rows,
            "2025 Estimate $646,244 supporting 51 community-led projects")
        self.assertTrue(x["2025_dashboard_population_and_scope_verified"])
        self.assertEqual(x["nominal_difference_approved_vs_estimate_cad"],"37500")
        self.assertTrue(x["difference_is_not_verified_unpaid_funds"])
    def test_missing_dashboard_not_confirmed(self):
        x=compare_brampton_arts_dashboard([],"")
        self.assertFalse(x["2025_dashboard_population_and_scope_verified"])
        self.assertNotIn("nominal_difference_approved_vs_estimate_cad",x)

import unittest
from src.observatory.integrity import (
    report_pdf_links,council_items,neutral_queue,research_questions,grants_from_pdf,
)
class IntegrityTests(unittest.TestCase):
    def test_purchasing_index_only_official_pdf(self):
        doc='''<a href="/wp-content/uploads/2026/11/oct.pdf">October 2026 Non-Competitive Acquisitions Report</a>
        <a href="https://evil.example/x.pdf">June 2026 Non-Competitive Acquisitions Report</a>
        <a href="/wp-content/uploads/2026/09/a.pdf">August 2026 Competitive Acquisitions Report</a>'''
        urls=report_pdf_links(doc)
        self.assertEqual(len(urls),1)
        self.assertTrue(urls[0].endswith("oct.pdf"))
    def test_toronto_items_neutral(self):
        sample='''<h3>GG28.2 - Amendment to Purchase Order 6051950</h3><p>
          Increase to deliver additional inspections. Total was changed.</p>
          <h3>GG28.4 - Non-Competitive Contract for Specialized Software</h3>
          <p>City invokes exclusive supplier.</p>'''
        records=council_items(sample)
        self.assertEqual(len(records),2)
        self.assertEqual(records[0]["category"],"CONTRACT_AMENDMENT_FOR_REVIEW")
        self.assertEqual(records[1]["category"],"NONCOMPETITIVE_DECISION_FOR_REVIEW")
        self.assertIn("additional inspections",records[0]["source_text_excerpt"])
        self.assertFalse(any("fraud" in str(r).lower() for r in records))
    def test_grant_repeats_never_legal_entity_findings(self):
        rows=[
         {"year":"2025","organization_name_as_reported":"Sample Community Inc.",
          "source_url":"https://www.brampton.ca/test", "approved_amount_as_reported":"$5,000",
          "program_area_as_reported":"Arts","source_page":1},
         {"year":"2026","organization_name_as_reported":"Sample Community Inc",
          "source_url":"https://www.brampton.ca/test2","approved_amount_as_reported":"$6,000",
          "program_area_as_reported":"Arts","source_page":1}
        ]
        queue,repeats=neutral_queue([],[],rows)
        self.assertEqual(len(repeats),1)
        self.assertFalse(repeats[0]["identity_verified"])
        self.assertEqual(len(queue),2)
        self.assertTrue(all(x["status"]=="RESEARCH_ONLY_NOT_ALLEGATION" for x in queue))
    def test_review_questions_require_corrobation(self):
        self.assertTrue(any("policy" in q or "exception" in q for q in research_questions("NONCOMPETITIVE_PURCHASE")))

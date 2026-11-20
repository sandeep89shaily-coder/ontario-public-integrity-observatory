import json,tempfile,unittest
from pathlib import Path
from src.observatory.grant_relationships import analyze,run
def award(year,name,area="Recreation",stream="Developing",amt="10000"):
    return {"year":year,"organization_as_published":name,"program_area":area,
            "grant_stream":stream,"approved_amount_cad":amt,
            "source_url":"https://www.brampton.ca/official.pdf","source_page":1}
class RelationshipResearchTests(unittest.TestCase):
    def test_recurrence_not_misconduct_and_priority_area_not_project_purpose(self):
        summary,profiles,links,purposes,held=analyze([
          award("2024","Example Group",amt="5000"),
          award("2025","Example Group","Arts and Culture",amt="7000"),
          award("2026","Other Group",amt="9000")])
        self.assertEqual(summary["repeat_name_groups"],1)
        self.assertEqual(summary["groups_with_priority_area_change"],1)
        self.assertEqual(profiles[0]["published_approved_total_cad"],"12000")
        self.assertIn("NOT_IN_AWARD_LIST",profiles[0]["project_purpose_status"])
        self.assertEqual(summary["cross_recipient_relationships_documented"],0)
    def test_unsourced_relationship_never_added(self):
        awards=[award("2025","Example Group"),award("2025","Other Group")]
        link={"recipient_a":"Example Group","recipient_b":"Other Group",
              "relationship_type":"REGISTERED_SHARED_DIRECTOR",
              "source_url":"https://www.ontario.ca/registry","source_date":"2025-04-02",
              "source_excerpt":"Two organizations share the same director under a purported listing",
              "registry_record_id":"","human_reviewed":"no"}
        summary,profiles,links,purposes,held=analyze(awards,relation_rows=[link])
        self.assertEqual(len(links),0)
        self.assertEqual(held[0]["status"],"RELATIONSHIP_NOT_SUPPORTED")
    def test_city_purpose_supported_without_claiming_results(self):
        awards=[award("2025","Example Group")]
        purpose={"year":"2025","recipient_name":"Example Group","project_title":"Program A",
          "project_description":"A specific activity funded by the City in 2025.",
          "source_url":"https://www.brampton.ca/approved.pdf",
          "evidence_kind":"CITY_PUBLISHED_PROJECT","human_reviewed":"yes"}
        a,b,c,p,held=analyze(awards,purpose_rows=[purpose])
        self.assertEqual(len(p),1)
        self.assertEqual(p[0]["status"],"CITY_PROJECT_PURPOSE_DOCUMENTED")
        self.assertEqual(a["actual_payments_verified"],0)
    def test_end_to_end_offline_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"awards.json").write_text(json.dumps([
                award("2024","A"),award("2025","A"),award("2026","B")]))
            (root/"purpose.csv").write_text("year,recipient_name,project_title,project_description,source_url,evidence_kind,human_reviewed\n")
            (root/"relationships.csv").write_text("recipient_a,recipient_b,relationship_type,source_url,source_date,source_excerpt,registry_record_id,human_reviewed\n")
            summary=run(root/"awards.json",root/"out",root/"purpose.csv",root/"relationships.csv")
            self.assertEqual(summary["repeat_name_groups"],1)
            self.assertTrue((root/"out/recipient_continuity.csv").exists())

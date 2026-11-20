import unittest,tempfile,json
from pathlib import Path
from src.observatory.grant_project_cases import prepare,run
def a(year,name,amt):
 return {"year":year,"organization_as_published":name,
   "grant_stream":"Amplifying","program_area":"Recreation",
   "approved_amount_cad":amt,"source_url":"https://www.brampton.ca/awards.pdf","source_page":1}
class ProjectCases(unittest.TestCase):
 def test_no_improper_conflation_of_other_funding_with_city_grant(self):
  awards=[a("2024","Org A","10000"),a("2025","Org A","12000")]
  ev={"focus":[{"recipient":"Org A"}],
   "activities":[{"year":"2025","recipient":"Org A","project":"Training workshops",
     "description":"The organization advertised training workshops but no close-out was supplied.",
     "source_url":"https://example.org/news","source_publisher":"Org A",
     "evidence_type":"RECIPIENT_PROMOTION","activity_status":"PLANNED_OR_PROMOTED","scope_verified_by_city":False}],
   "external_funding":[{"year":"2024","recipient":"Org A","funder":"Peel Region",
     "program":"Core Fund","reported_award_amount_cad":"22000",
     "amount_basis":"FUNDER_PUBLISHED_FUNDING_NOT_RECONCILED_PAYMENTS",
     "source_url":"https://peelregion.ca/funding","same_project_as_city_grant_verified":False}],
   "relationships":[]}
  s,c,h=prepare(awards,ev)
  self.assertEqual(c[0]["city_approved_total_cad"],"22000")
  self.assertEqual(c[0]["other_funders"][0]["other_funder_reported_amount_cad"],"22000")
  self.assertTrue(c[0]["other_funders"][0]["do_not_add_to_city_award_total"])
  self.assertFalse(c[0]["activities"][0]["city_contract_scope_verified"])
  self.assertEqual(s["confirmed_duplicate_funding"],0)
 def test_reject_unsubstantiated_city_scope_and_risky_relationship(self):
  awards=[a("2025","Org A","2500")]
  ev={"focus":[{"recipient":"Org A"}],
   "activities":[{"year":"2025","recipient":"Org A","project":"Training workshops",
      "description":"An association described a training event, not a city-approved project scope.",
      "source_url":"https://example.org","source_publisher":"Org A",
      "evidence_type":"RECIPIENT_PROMOTION","activity_status":"PLANNED_OR_PROMOTED","scope_verified_by_city":True}],
   "external_funding":[],"relationships":[{"recipient":"Org A","related_entity":"Company B",
     "evidence_type":"RECIPIENT_REPORTED_COLLABORATION",
     "source_url":"https://example.org","description":"A participant said they have jointly funded the same staff costs.",
     "financial_relationship_verified":True,"related_entity_is_an_abf_recipient_verified":False}]}
  s,c,h=prepare(awards,ev)
  self.assertEqual(len(h),2)
  self.assertFalse(c[0]["activities"])
  self.assertFalse(c[0]["reported_collaborations"])
 def test_invalid_year_cannot_attach_mismatched_project(self):
  s,c,h=prepare([a("2024","Org A","2500")],
    {"focus":[{"recipient":"Org A"}],
     "activities":[{"year":"2025","recipient":"Org A","project":"Wrong year",
      "description":"No matching year appeared in the City award data for this entry.",
      "source_url":"https://example.org","source_publisher":"Org A",
      "evidence_type":"RECIPIENT_PROMOTION","activity_status":"PLANNED_OR_PROMOTED","scope_verified_by_city":False}]})
  self.assertEqual(len(h),1)

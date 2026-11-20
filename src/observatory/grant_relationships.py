"""Grant recipient continuity, purpose and *documented* relationship analysis.

This research system does not infer fraud, personal relationships, or common
control from a name, address, nationality, broad program category or award amount.
No private personal identifiers are stored.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,re
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

PURPOSE_KINDS={"CITY_PUBLISHED_PROJECT","PUBLIC_SIGNED_GRANT_RECORD","RECIPIENT_SELF_REPORTED"}
LINK_KINDS={"CORPORATE_IDENTITY","PUBLICLY_DECLARED_PARTNERSHIP","REGISTERED_SHARED_DIRECTOR",
            "DOCUMENTED_FINANCIAL_TRANSFER","PUBLICLY_CONFIRMED_SHARED_OFFICER"}

def key(name):
    return " ".join(re.sub(r"[^a-z0-9]+"," ",str(name or "").casefold()).split())

def official_url(url):
    p=urlsplit(str(url or ""))
    return p.scheme=="https" and bool(p.hostname) and not p.username

def read_evidence(path,required):
    if not path:return []
    with Path(path).open(newline="",encoding="utf-8-sig") as handle:
        reader=csv.DictReader(handle)
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError("Missing evidence CSV columns")
        return list(reader)

def relationships(known_keys,rows):
    accepted=[];held=[]
    for r in rows:
        left,right=key(r.get("recipient_a")),key(r.get("recipient_b"))
        relationship=r.get("relationship_type","")
        date=r.get("source_date","")
        try:dt.date.fromisoformat(date)
        except ValueError: date=""
        evidence={
            "recipient_a":r.get("recipient_a"),"recipient_b":r.get("recipient_b"),
            "relationship_type":relationship,"source_url":r.get("source_url"),
            "source_date":date,"quote":r.get("source_excerpt",""),
            "status":"DOCUMENTED_RELATIONSHIP_NEEDS_CONTEXT_NOT_MISCONDUCT",
            "limits":"Relationship is not an improper interest and does not imply collusion or fraud."}
        good=(left!=right and left in known_keys and right in known_keys and
              relationship in LINK_KINDS and official_url(r.get("source_url")) and
              len(r.get("source_excerpt","").strip())>=25 and
              r.get("human_reviewed","").lower()=="yes" and bool(date) and
              (relationship not in ("CORPORATE_IDENTITY","REGISTERED_SHARED_DIRECTOR",
                                  "PUBLICLY_CONFIRMED_SHARED_OFFICER")
               or bool(r.get("registry_record_id","").strip())))
        if good:accepted.append(evidence)
        else:held.append({"status":"RELATIONSHIP_NOT_SUPPORTED","recipient_a":r.get("recipient_a"),
                          "recipient_b":r.get("recipient_b"),"reason":"Missing source, human review, dated evidence, registered identity, or valid recipient"})
    return accepted,held

def project_purposes(known_year_keys,rows):
    accepted=[];held=[]
    for r in rows:
        k=(r.get("year"),key(r.get("recipient_name")))
        doc_type=r.get("evidence_kind")
        good=(k in known_year_keys and doc_type in PURPOSE_KINDS and
              r.get("human_reviewed","").lower()=="yes" and official_url(r.get("source_url")) and
              len(r.get("project_title","").strip())>=3 and
              len(r.get("project_description","").strip())>=20)
        if good:
            accepted.append({
                "year":k[0],"recipient_as_published":r["recipient_name"],
                "project_title":r["project_title"],"project_description":r["project_description"],
                "source_url":r["source_url"],"evidence_kind":doc_type,
                "status":("CITY_PROJECT_PURPOSE_DOCUMENTED" if doc_type=="CITY_PUBLISHED_PROJECT"
                         else "DOCUMENTED_CLAIM_NOT_INDEPENDENT_OUTCOME_VERIFICATION")})
        else:
            held.append({"status":"PURPOSE_NOT_VERIFIED","recipient":r.get("recipient_name"),"year":r.get("year")})
    return accepted,held

def analyze(awards,purpose_rows=None,relation_rows=None):
    if not isinstance(awards,list):raise ValueError("Expected a source award list")
    by_name=defaultdict(list);seen=set()
    for award in awards:
        for f in ("year","organization_as_published","program_area","grant_stream",
                  "approved_amount_cad","source_url","source_page"):
            if f not in award:raise ValueError("Missing source award field "+f)
        if not official_url(award["source_url"]):raise ValueError("Source URL must be HTTPS")
        ident=key(award["organization_as_published"])
        if not ident:raise ValueError("Blank printed recipient")
        # A name match is not a verified legal-entity match, even when repeated.
        by_name[ident].append(award)
    known_year_keys={(r["year"],k) for k,group in by_name.items() for r in group}
    purposes,purpose_held=project_purposes(known_year_keys,purpose_rows or [])
    relations,rel_held=relationships(set(by_name),relation_rows or [])
    p_index=defaultdict(list)
    for p in purposes:p_index[(p["year"],key(p["recipient_as_published"]))].append(p)
    longitudinal=[];area_switches=[];stream_switches=[]
    for k,group in by_name.items():
        years=sorted({g["year"] for g in group})
        if len(years)<2:continue
        group=sorted(group,key=lambda x:(x["year"],x["source_page"],x.get("table_row",0)))
        areas=sorted({g["program_area"] for g in group})
        streams=sorted({g["grant_stream"] for g in group})
        amount=sum((Decimal(str(g["approved_amount_cad"])) for g in group),Decimal("0"))
        object_id=hashlib.sha256(k.encode()).hexdigest()[:14]
        r={
          "case_id":"recipient-name-"+object_id,
          "name_as_published":group[0]["organization_as_published"],
          "identity_status":"NORMALIZED_PUBLISHED_NAME_ONLY_UNVERIFIED_LEGAL_IDENTITY",
          "years":years,"year_count":len(years),"number_of_award_entries":len(group),
          "published_approved_total_cad":str(amount),
          "priority_areas":areas,"grant_streams":streams,
          "area_changed":len(areas)>1,"stream_changed":len(streams)>1,
          "project_purpose_status":("EVIDENCE_ADDED" if any((g["year"],k) in p_index for g in group)
                                   else "SPECIFIC_FUNDED_PROJECT_NOT_IN_AWARD_LIST"),
          "awards":[{"year":g["year"],"approved_amount_cad":g["approved_amount_cad"],
                     "priority_area":g["program_area"],"stream":g["grant_stream"],
                     "source_url":g["source_url"],"source_page":g["source_page"],
                     "specific_project_purpose_evidence":p_index.get((g["year"],k),[])}
                    for g in group],
          "interpretation":"Continuity of a printed recipient name, not evidence of favoritism or fraud."}
        longitudinal.append(r)
        if r["area_changed"]:area_switches.append(r["case_id"])
        if r["stream_changed"]:stream_switches.append(r["case_id"])
    longitudinal.sort(key=lambda r:(-r["year_count"],-Decimal(r["published_approved_total_cad"]),
                                   r["name_as_published"]))
    summary={
      "scope":"Brampton Advance Brampton Fund 2024–2026",
      "published_award_entries":len(awards),
      "printed_name_groups":len(by_name),
      "repeat_name_groups":len(longitudinal),
      "three_year_name_groups":sum(x["year_count"]==3 for x in longitudinal),
      "groups_with_priority_area_change":len(area_switches),
      "groups_with_stream_change":len(stream_switches),
      "specific_project_purpose_records_reviewed":len(purposes),
      "cross_recipient_relationships_documented":len(relations),
      "actual_payments_verified":0,"fraud_findings":0,
      "data_limitations":[
        "Published priority area (e.g. Arts and Culture) is not the funded project's actual purpose.",
        "The public recipient lists do not establish common directors, family ties, supplier payments, or conflicts.",
        "A repeated printed name is not necessarily proof of legal entity continuity.",
        "No adverse conclusion can be based on amount, name frequency, or shared program area alone."]}
    return summary,longitudinal,relations,purposes,rel_held+purpose_held

def run(awards,out,purposes=None,relationships_csv=None):
    awards=json.loads(Path(awards).read_text(encoding="utf-8"))
    purp=read_evidence(purposes,("year","recipient_name","project_title","project_description",
                  "source_url","evidence_kind","human_reviewed"))
    links=read_evidence(relationships_csv,("recipient_a","recipient_b","relationship_type",
                  "source_url","source_date","source_excerpt","registry_record_id","human_reviewed"))
    summary,profiles,connections,projects,holds=analyze(awards,purp,links)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for name,obj in (("summary.json",summary),("cross_year_recipient_histories.json",profiles),
                     ("documented_cross_recipient_relationships.json",connections),
                     ("specific_project_purposes.json",projects),("evidence_held.json",holds)):
        (out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding="utf-8")
    fields=["recipient","years","approved_total_cad","priority_areas","streams",
            "priority_area_changed","stream_changed","specific_project_purpose"]
    with (out/"recipient_continuity.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for x in profiles:
            writer.writerow({"recipient":x["name_as_published"],"years":", ".join(x["years"]),
              "approved_total_cad":x["published_approved_total_cad"],
              "priority_areas":"; ".join(x["priority_areas"]),
              "streams":"; ".join(x["grant_streams"]),
              "priority_area_changed":x["area_changed"],"stream_changed":x["stream_changed"],
              "specific_project_purpose":x["project_purpose_status"]})
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--awards",required=True)
    p.add_argument("--out",default="local_results/recipient_relationships")
    p.add_argument("--purpose-evidence",default="config/grant_project_purposes.csv")
    p.add_argument("--relationship-evidence",default="config/grant_relationship_evidence.csv")
    a=p.parse_args()
    print(json.dumps(run(a.awards,a.out,a.purpose_evidence,a.relationship_evidence),indent=2))
if __name__=="__main__":main()

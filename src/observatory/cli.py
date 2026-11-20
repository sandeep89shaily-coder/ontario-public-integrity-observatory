"""An offline, non-accusatory repeat-award evidence check."""
import argparse
import csv
import json
from collections import defaultdict
from urllib.parse import urlparse

REQUIRED = {'municipality','contract_id','vendor_name','award_date','award_amount_cad','source_url'}


def investigate(path):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or ()):
            raise ValueError('Missing required award fields')
        groups = defaultdict(list)
        for row in reader:
            if not row['vendor_name'].strip() or not row['contract_id'].strip():
                raise ValueError('Missing vendor or contract identifier')
            source = urlparse(row['source_url'])
            if source.scheme != 'https' or not source.hostname:
                raise ValueError('Source URL must be HTTPS')
            # Name-only matching is a review candidate, not legal entity resolution.
            key = ' '.join(row['vendor_name'].casefold().split())
            groups[key].append(row)
    return {'status':'NAME_ONLY_REVIEW_CANDIDATES_NOT_FINDINGS', 'record_count':sum(map(len,groups.values())),
            'repeat_vendor_candidates':[
               {'name_as_recorded':items[0]['vendor_name'], 'award_count':len(items),
                'municipalities':sorted({item['municipality'] for item in items}),
                'contract_ids':[item['contract_id'] for item in items],
                'investigation_needed':'Verify legal entity, competition, prior performance and context'}
               for items in groups.values() if len(items)>1]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    args=parser.parse_args()
    print(json.dumps(investigate(args.input),indent=2))

if __name__=='__main__':
    main()

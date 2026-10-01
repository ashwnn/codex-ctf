# Synthetic fixture: no network, credentials, or real challenge data.
USERS = {"alice": {"role": "member"}, "ops": {"role": "admin"}}
RECORDS = {"r-1": {"owner": "alice", "body": "synthetic-alpha"}}


def read_record(record_id, principal):
    record = RECORDS.get(record_id)
    if record is None:
        return 404, {"error": "not found"}
    # TODO: authorization check; currently any authenticated principal can read.
    return 200, {"id": record_id, "body": record["body"]}

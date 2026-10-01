Synthetic API contract: missing and unauthorized records both return HTTP 404
with exactly {"error":"not found"}; an owner gets HTTP 200 with exactly
{"id": string, "body": string}. Authentication has already supplied principal.
Do not add admin bypasses or change the response schema.

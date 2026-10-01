Synthetic API contract: missing and unauthorized records both return
(404, {"error":"not found"}); an owner gets (200, {"id": string, "body": string}).
Authentication supplies principal. Keep the exact response shapes. Use Python
standard-library tools only.

python C:\RestoOps\apps\api\tests\phase10_test.py       

============================================================
  1. Health & Root Endpoints
============================================================
  [OK]   GET /health -> 200
  [OK]   health.status == 'healthy'
  [OK]   health.service present
  [OK]   GET / -> 200
  [OK]   root.docs present
  [OK]   GET /metrics -> 200 (Prometheus)
  [OK]   GET /openapi.json -> 200

============================================================
  2. Authentication Flow
============================================================
  [OK]   POST /auth/login -> 200 - status=200
  [OK]   Access token received
  [OK]   Refresh token received
  [OK]   GET /auth/me -> 200
  [OK]   me.email correct
  [OK]   me.organization_id present
  [OK]   POST /auth/refresh -> 200 - status=200
  [OK]   New access token issued
  [OK]   Login with wrong password -> 401
  [OK]   Unauthenticated leads list -> 401

============================================================
  3. Users
============================================================
  [OK]   GET /users -> 200 - status=200
  [OK]   Users list is a list
  [OK]   At least 1 user exists

============================================================
  4. Organizations
============================================================
  [OK]   GET /organizations/me -> 200 - status=200
  [OK]   Organization name present

============================================================
  5. Leads - CRUD + Pipeline
============================================================
  [OK]   POST /leads -> 201 - status=201
  [OK]   Lead ID returned
  [OK]   Lead company_name matches
  [OK]   GET /leads -> 200 - status=200
  [OK]   Leads list has items - total=729
  [OK]   GET /leads/{id} -> 200
  [OK]   PATCH /leads/{id} -> 200
  [OK]   Lead priority updated
  [OK]   POST /leads/{id}/pipeline/CONTACTED -> 200
  [OK]   Pipeline status updated
  [OK]   GET /leads/{id}/activity -> 200
  [OK]   Activity log has entries - count=3
  [OK]   GET /leads/{id}/verifications -> 200
  [OK]   GET /leads?search= -> 200
  [OK]   GET /leads?pipeline_status= filter -> 200

============================================================
  6. Leads - CSV Import
============================================================
  [OK]   POST /leads/import/csv -> 202 - status=202
  [OK]   CSV import total_rows returned - rows=2
  [OK]   At least 2 valid rows imported

============================================================
  7. Campaigns - CRUD + Actions
============================================================
  [OK]   POST /campaigns -> 201 - status=201
  [OK]   Campaign ID returned
  [OK]   Campaign name matches
  [OK]   GET /campaigns -> 200
  [OK]   At least 1 campaign
  [OK]   GET /campaigns/{id} -> 200
  [OK]   PATCH /campaigns/{id} -> 200
  [OK]   GET /campaigns/{id}/analytics -> 200 - status=200
  [OK]   GET /campaigns/{id}/leads -> 200

============================================================
  8. Quotes - Full Lifecycle
============================================================
  [OK]   POST /quotes -> 201 - status=201
  [OK]   Quote ID returned
  [OK]   Quote event date matches
  [OK]   Quote has items
  [OK]   GET /quotes -> 200
  [OK]   GET /quotes/{id} -> 200
  [OK]   PATCH /quotes/{id} -> 200 - status=200
  [OK]   POST /quotes/{id}/items -> 200 - status=200
  [OK]   POST /quotes/{id}/submit -> 200 - status=200
  [OK]   POST /quotes/{id}/approve -> 200 - status=200
  [OK]   POST /quotes/{id}/send -> 200 - status=200
  [OK]   POST /quotes/{id}/accept -> 200 (creates Order) - status=200        
  [OK]   Order ID returned from quote accept

============================================================
  9. Orders
============================================================
  [OK]   GET /orders -> 200 - status=200
  [OK]   Orders is a list
  [OK]   At least 1 order (from quote accept)
  [OK]   GET /orders/{id} -> 200

============================================================
  10. Conversations
============================================================
  [OK]   GET /conversations -> 200 - status=200
  [WARN] POST /conversations/analyze not implemented or Method Not Allowed   

============================================================
  11. AI Endpoints
============================================================
  [OK]   GET /ai/actions/pending -> 200 - status=200
  [OK]   GET /ai/activity -> 200 - status=200

============================================================
  12. Calls
============================================================
  [OK]   GET /calls -> 200 - status=200
  [OK]   Calls is a list
  [OK]   POST /calls -> 201 - status=201
  [OK]   Call ID returned
  [OK]   GET /calls/{id} -> 200

============================================================
  13. Notifications
============================================================
  [OK]   GET /notifications -> 200 - status=200
  [OK]   GET /notifications/unread-count -> 200 - status=200

============================================================
  14. Verification
============================================================
  [OK]   GET /verification/jobs -> 200 - status=200
  [OK]   POST /verification/check -> 200 - status=200

============================================================
  15. Suppression List
============================================================
  [OK]   POST /suppression -> 201 - status=201
  [OK]   GET /suppression -> 200 - status=200
  [OK]   Suppression list is a list
  [OK]   DELETE /suppression/{id} -> 204 - status=204

============================================================
  16. Restaurants
============================================================
  [OK]   POST /restaurants -> 201 - status=201
  [OK]   GET /restaurants -> 200 - status=200
  [OK]   GET /restaurants/{id} -> 200
  [OK]   PATCH /restaurants/{id} -> 200 - status=200
  [OK]   DELETE /restaurants/{id} -> 204 - status=204

============================================================
  17. Webhooks
============================================================
  [OK]   GET /webhooks -> 200 - status=200

============================================================
  18. API Documentation
============================================================
  [OK]   GET /docs -> 200 (Swagger UI)
  [OK]   GET /redoc -> 200 (ReDoc)

============================================================
  19. Cleanup (Delete test lead)
============================================================
  [OK]   DELETE /leads/{id} -> 204 - status=204
  [OK]   GET deleted lead -> 404

============================================================
  20. Edge Cases & Security
============================================================
  [OK]   GET non-existent lead -> 404
  [OK]   Duplicate suppression -> 400/409 or 201 (idempotent)
  [OK]   Import non-CSV file -> 400

============================================================
  PHASE 10 TEST REPORT - 2026-09-19 02:22:33
============================================================
  Passed:   95
  Failed:   0
  Warnings: 1
  Total:    95
  Score:    100.0%
============================================================

  ALL TESTS PASSED - System is healthy!

PS C:\RestoOps>

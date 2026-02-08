# Phase 9: Notifications

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Multi-channel notification system for events and alerts. Moved earlier in the plan (was old Phase 15) because approvals (Phase 10), drift detection (Phase 11), and audit anomaly alerts all need notifications to be useful.

## Deliverables
- Email notifications (SMTP)
- In-app notification center (PostgreSQL-backed initially, upgraded to Valkey pub/sub in Phase 12)
- Webhook integrations (outbound)
- Notification templates (Jinja2)
- User notification preferences (per-channel, per-category)
- Notification history
- Notification center UI in frontend

## Dependencies
- Phase 3 complete (user/permission context)

## Key Questions for Refinement
- What notification categories to support?
- How to handle notification failures?
- Should notifications support batching/digest?
- What webhook payload format?
- How to handle email template rendering?

## Estimated Tasks
~8-10 tasks (to be refined before implementation)

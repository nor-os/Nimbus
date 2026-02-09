# Phase 13: Real-time & Caching (Valkey)

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Add Valkey (community Redis fork, same API) to infrastructure for caching and pub/sub. Implement Socket.IO server for WebSocket connections and GraphQL subscriptions for real-time updates. This phase provides the infrastructure layer that enables real-time features in Phase 14+ and upgrades the notification system from Phase 9 with live delivery.

*Was old Phase 19 (Real-time Updates). Moved earlier to enable real-time features in Phase 14 (Advanced Audit).*

## Deliverables
- **Valkey added to Docker Compose** (`valkey/valkey:8-alpine`, port 6379)
- Socket.IO server integration with Valkey adapter (multi-process pub/sub)
- Room-based subscriptions (tenant:{id}, user:{id}, resource:{id})
- GraphQL subscriptions implementation
- Real-time resource state updates
- Live notification delivery (upgrade Phase 9 in-app notifications to Valkey pub/sub)
- Connection management & reconnection in frontend
- Caching layer (permissions, tenant config, session data)

## Dependencies
- Phase 8 complete (CMDB for resource updates)
- Phase 9 complete (notifications for live delivery upgrade)

## Key Questions for Refinement
- What events should be real-time vs polling?
- How to handle disconnection/reconnection?
- Should offline changes be queued?
- What's the acceptable latency target?
- What data should be cached in Valkey?
- Cache invalidation strategy (TTL, event-driven, hybrid)?

## Estimated Tasks
~8-10 tasks (to be refined before implementation)

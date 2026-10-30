# 0010 — Docker port bindings default to loopback-only

## Status
Accepted

## Context
`docker-compose.yml`'s port mappings originally bound every service to all
interfaces (`0.0.0.0`) — fine on a laptop behind a home router/NAT, where
nothing external can reach those ports anyway, but not fine once the same
compose file is deployed to a VM with a routable (even if VPN-only)
network presence. Discovered while preparing production-VM deployment
guidance: `warehouse-db` (3306/3308), `landing-zone` (8333/8888), and
`metabase` (3000) would all be reachable from anywhere that could route to
the host unless someone remembered to change the bindings at deploy time —
a manual step that's easy to forget, with real consequences if forgotten
(the DB and landing zone have no business being internet- or even
VPN-network-facing at all).

Separately, VM deployment investigation surfaced that a target VM may not
be dedicated to this project — it can carry other live, unrelated services
(confirmed live: a pre-existing MySQL instance and a separate web app on
the same host) — raising the cost of any networking mistake.

## Decision
Bind every service's host ports to `127.0.0.1` explicitly in
`docker-compose.yml` itself, rather than leaving the default `0.0.0.0` and
documenting "remember to change this for production" as a manual runbook
step. `warehouse-db` and `landing-zone` have no reason to ever be reachable
beyond the host they run on — Metabase already reaches `warehouse-db` over
the internal `cdw-net` bridge network regardless of host-port binding.
Metabase's own port is bound to loopback too; real end-user access is
meant to go through an SSH tunnel for quick checks, or a reverse proxy
(TLS-terminating, bound to the host's public interface) for actual
production use — Metabase has no TLS of its own.

## Consequences
- Secure by default on any new environment (local dev or a fresh VM)
  without a manual hardening step that could be forgotten.
- Local development is unaffected — `localhost` already resolves to
  `127.0.0.1` on the same machine, so nothing changes for a laptop-only
  workflow.
- A VM deploy now requires a deliberate additional step (SSH tunnel or
  reverse-proxy setup) to make Metabase reachable by real users — a small
  amount of extra setup traded for not exposing anything by accident.
- If a host is already behind its own trusted network boundary and
  external reachability is actually wanted without a proxy, the binding
  has to be explicitly changed back to `0.0.0.0:...` — documented inline
  in `docker-compose.yml` at each port mapping.

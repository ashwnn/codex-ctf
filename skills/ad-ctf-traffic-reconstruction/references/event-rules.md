# A/D infrastructure context

Source: user-supplied `Rules.pdf`, sections 4 and 6, September 2026.
The user requested A/D-only operation without phase/model-eligibility gates.
This reference describes expected infrastructure; it is not a launcher policy.
Organizer announcements and challenge text may change these assumptions.

- Identical vulnerable services, usually Docker containers, on a private team VM
  with root access and backup source ZIPs. Record deployed hashes, mounts,
  capabilities, listeners, run user and the actual boot path.
- WireGuard provides team access. Peers are reached through central reverse TCP
  proxies per service, not by connecting to peer VMs. Shared proxy addresses are
  not reliable attacker identities. VSCode Web, Tulip, SSH and PCAP download
  utilities are supporting infrastructure, not service attack surfaces.
- About two minutes per tick. One new flag per service per tick; flag lifetime is
  five ticks (about ten minutes). Public flag IDs locate objects; IDs do not confer
  authorization. Preserve placement, retrieval, expiry and persistence.
- Offense, defense and uptime contribute to scoring. Checker exercises ordinary
  service behavior and expects specific responses. Preserve UI, flow and response
  shape; a patch that breaks the checker is unsuccessful.
- Own-service ingress/egress PCAPs support reconstruction. Team 1 is the NOP test
  team. Use the actual published interface and targets, never invented addresses.
- Service descriptions bound relevant ports/directories. Nondestructive local
  reproductions with synthetic flags and bounded tests protect evidence and uptime.
- Keep credentials, real flags, private challenge source and findings in the
  ignored service workspace. Do not publish solutions or raw captures.

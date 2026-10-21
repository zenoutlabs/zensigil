# A non-commerce example: the core has no Amazon-specific concepts.
rule "Support triage":
    for ticket in tickets:
        when ticket.priority == "high" and ticket.waiting_hours > 4:
            propose escalate(
                ticket_id: ticket.id,
                queue: "priority review",
                explanation: ticket.id + " is high priority and has waited " + text(ticket.waiting_hours) + " hours, longer than the 4-hour threshold.",
                evidence: ["Priority: " + ticket.priority, "Waiting time: " + text(ticket.waiting_hours) + " hours; threshold: 4 hours"]
            )

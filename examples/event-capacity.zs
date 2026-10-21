# Review attendance for a workshop, club, class, or community event.
rule "Check event capacity":
    for session in sessions:
        let remaining = session.capacity - session.registered
        when remaining < 0:
            propose review_capacity(
                id: session.id,
                extra_places_needed: 0 - remaining,
                explanation: session.title + " has " + text(session.registered) + " registrations for " + text(session.capacity) + " places. Review the " + text(0 - remaining) + " extra registrations."
            )
        otherwise:
            when remaining == 0:
                say session.title + ": full."
            otherwise:
                say session.title + ": " + text(remaining) + " places available."

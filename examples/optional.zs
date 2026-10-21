rule "Optional fields":
    for person in people:
        when has(person, "email") and person.email != null:
            propose contact_review(name: person.name, email: person.email)
        otherwise:
            say person.name + " has no email address"

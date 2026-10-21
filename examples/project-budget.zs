# Keep amounts as whole cents so comparisons and subtraction stay exact.
# Input uses one currency for the entire project list.
rule "Review project budgets":
    for project in projects:
        when project.spent_cents > project.budget_cents:
            let over = project.spent_cents - project.budget_cents
            propose review_budget(
                id: project.id,
                over_budget_cents: over,
                currency: currency,
                explanation: project.title + " is " + text(over) + " cents above its " + text(project.budget_cents) + "-cent budget.",
                evidence: [text(project.spent_cents) + " cents spent - " + text(project.budget_cents) + " cents budgeted = " + text(over) + " cents over"]
            )
        otherwise:
            say project.title + ": within budget."

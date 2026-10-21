rule "Duplicate inputs":
    for item in items:
        propose review(sku: item.sku, reason: "Check stock")

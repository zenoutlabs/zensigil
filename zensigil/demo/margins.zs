# Synthetic, simplified contribution margin. Amounts are integer cents.
# Real commerce models need complete fees, returns, tax and cost definitions.
fn profit_cents(item):
    return item.price_cents - item.cost_cents - item.fees_cents

rule "Margin review":
    for item in products:
        when item.price_cents <= 0:
            say "Skipped " + item.sku + ": price must be positive"
        otherwise:
            let profit = profit_cents(item)
            # Compare integer products instead of rounding a margin percentage.
            when profit * 100 < item.price_cents * 20:
                propose review_margin(
                    sku: item.sku,
                    profit_cents: profit,
                    reason: "Contribution margin is below 20 percent"
                )

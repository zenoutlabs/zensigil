# A reusable stock-review program. Edit policy in the input data.
# Keep quantity/threshold decisions exact for decimal input rates.
require policy.target_days >= policy.review_below_days, "Target days must be at least the review threshold. Update policy.target_days or policy.review_below_days."

rule "Stock review":
    for item in inventory:
        when item.discontinued:
            say item.sku + ": skipped because this product is discontinued."
        otherwise:
            let daily = get(item, "daily_sales", null)
            when daily == null:
                say item.sku + ": needs sales data before stock coverage can be calculated."
            otherwise:
                when daily == 0:
                    say item.sku + ": no reorder proposed because average daily sales is zero."
                otherwise:
                    let days = item.stock / daily
                    let shown_days = text(round(days, 2))
                    when needs_review(item.stock, daily, policy.review_below_days):
                        let quantity = reorder_units(item.stock, daily, policy.target_days)
                        propose reorder(
                            sku: item.sku,
                            quantity: quantity,
                            target_days: policy.target_days,
                            explanation: item.sku + " has about " + shown_days + " days of stock, below the " + text(policy.review_below_days) + "-day review threshold. Propose " + text(quantity) + " units to reach at least " + text(policy.target_days) + " days.",
                            evidence: [
                                text(item.stock) + " units / " + text(daily) + " average daily sales = about " + shown_days + " days of stock",
                                "Round up (" + text(daily) + " average daily sales * " + text(policy.target_days) + " target days - " + text(item.stock) + " units) = " + text(quantity) + " units"
                            ]
                        )
                    otherwise:
                        say item.sku + ": no reorder needed; about " + shown_days + " days of stock meets the " + text(policy.review_below_days) + "-day threshold."

# Helpers keep decimal rates exact; the review rule above stays readable.
fn needs_review(stock, daily, threshold):
    let rate = fraction(daily)
    return stock * rate.denominator < rate.numerator * threshold

fn reorder_units(stock, daily, target):
    let rate = fraction(daily)
    return ceil_div(rate.numerator * target, rate.denominator) - stock

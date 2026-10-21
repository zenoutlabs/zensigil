# Recommend stock to cover 30 days, when coverage falls below 14.
rule "Restock review":
    for item in inventory:
        when item.discontinued == false:
            let daily = get(item, "daily_sales", null)
            when daily == null:
                say "Skipped " + item.sku + ": sales missing"
            otherwise:
                when daily > 0:
                    let days = item.stock / daily
                    when days < 14:
                        propose reorder(
                            sku: item.sku,
                            quantity: ceil(daily * 30 - item.stock),
                            target_days: 30
                        )
                otherwise:
                    say "Skipped " + item.sku + ": daily sales must be positive"

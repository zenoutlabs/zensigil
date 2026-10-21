rule "Shipment discrepancies":
    for shipment in shipments:
        when shipment.received < shipment.expected:
            propose review_shipment(
                shipment_id: shipment.id,
                missing_units: shipment.expected - shipment.received,
                reason: "Received fewer units than expected"
            )
        otherwise:
            when shipment.received > shipment.expected:
                propose review_shipment(
                    shipment_id: shipment.id,
                    extra_units: shipment.received - shipment.expected,
                    reason: "Received more units than expected"
                )

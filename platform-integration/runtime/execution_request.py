"""Validate execution requests routed to Product Factory."""

FACTORY_ID = "factory.product-factory"
CAPABILITY_ID = "capability.product-definition"


def validate_execution_request(request, contract_validator):
    """Validate schema, routing, and input work identity.

    This function does not read handoff payloads, authorize execution,
    or create Product Factory sessions.
    """
    contract_validator.validate("execution-request", request)

    target = request["target"]

    if target["factory_id"] != FACTORY_ID:
        raise ValueError(
            f"Incorrect target factory: {target['factory_id']}"
        )

    if target["capability_id"] != CAPABILITY_ID:
        raise ValueError(
            f"Incorrect target capability: {target['capability_id']}"
        )

    expected_work = request["work"]

    for index, handoff in enumerate(request["inputs"]):
        if handoff["work"] != expected_work:
            raise ValueError(
                f"Input handoff {index} has a mismatched work context"
            )

        receiver = handoff["receiver"]

        if receiver != target:
            raise ValueError(
                f"Input handoff {index} targets a different receiver"
            )

    return True

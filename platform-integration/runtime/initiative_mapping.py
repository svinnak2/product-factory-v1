"""Normalize AI-PDLC Platform work types for Product Factory execution."""

WORK_TYPE_MAPPING = {
    "new-product": ("NEW_PRODUCT", "PRODUCT_CREATION", None),
    "new-capability": ("NEW_CAPABILITY", "PRODUCT_EVOLUTION", None),
    "new-feature": ("NEW_FEATURE", "PRODUCT_EVOLUTION", None),
    "development-defect": ("DEFECT", "PRODUCT_EVOLUTION", "DEVELOPMENT"),
    "operations-defect": ("DEFECT", "PRODUCT_EVOLUTION", "OPERATIONS"),
}

REQUIRED_FIELDS = (
    "initiative_id",
    "title",
    "problem_or_opportunity",
    "desired_outcome",
)


def normalize_initiative(work_type, initiative):
    """Return a validated, normalized Product Factory initiative.

    The work type determines the default context. An explicitly supplied
    development context must agree with that default; exceptions require
    separate review rather than silent reassignment.
    """
    if work_type not in WORK_TYPE_MAPPING:
        raise ValueError(f"Unsupported platform work type: {work_type}")

    if not isinstance(initiative, dict):
        raise ValueError("Initiative must be a dictionary")

    missing = [
        field for field in REQUIRED_FIELDS
        if not isinstance(initiative.get(field), str)
        or not initiative[field].strip()
    ]
    if missing:
        raise ValueError(
            "Missing required initiative fields: " + ", ".join(missing)
        )

    initiative_type, context, defect_origin = WORK_TYPE_MAPPING[work_type]

    result = dict(initiative)

    for field, expected in (
        ("initiative_type", initiative_type),
        ("development_context", context),
    ):
        supplied = result.get(field)
        if supplied is not None and supplied != expected:
            raise ValueError(
                f"{field} conflicts with platform work type "
                f"{work_type}: expected {expected}, received {supplied}"
            )
        result[field] = expected

    supplied_origin = result.get("defect_origin")
    if supplied_origin is not None and supplied_origin != defect_origin:
        raise ValueError(
            f"defect_origin conflicts with platform work type {work_type}"
        )
    result["defect_origin"] = defect_origin

    return {"schema_version": "2.0", "initiative": result}

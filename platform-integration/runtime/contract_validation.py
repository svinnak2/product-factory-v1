"""Validate integration payloads against official AI-PDLC contracts."""

import json
import zipfile
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


CONTRACTS = {
    "execution-request": "execution-request",
    "execution-result": "execution-result",
    "work-context": "work-context",
    "factory-handoff-envelope": "factory-handoff-envelope",
    "factory-interface-manifest": "factory-interface-manifest",
    "human-interaction-request": "human-interaction-request",
    "human-interaction-response": "human-interaction-response",
}


class PlatformContractValidator:
    """Validate platform contracts using their canonical schema IDs."""

    def __init__(self, platform_zip):
        platform_zip = Path(platform_zip)

        if not platform_zip.is_file():
            raise FileNotFoundError(platform_zip)

        self.schemas = {}
        resources = []

        with zipfile.ZipFile(platform_zip) as archive:
            names = archive.namelist()

            for contract_name in CONTRACTS.values():
                suffix = (
                    f"contracts/platform/{contract_name}/"
                    "0.1.0.schema.json"
                )

                matches = [
                    name for name in names
                    if name.endswith(suffix)
                ]

                if len(matches) != 1:
                    raise ValueError(
                        f"Expected one schema for {contract_name}; "
                        f"found {len(matches)}"
                    )

                schema = json.loads(archive.read(matches[0]))
                Draft202012Validator.check_schema(schema)

                schema_id = schema["$id"]
                self.schemas[contract_name] = schema
                resources.append(
                    (schema_id, Resource.from_contents(schema))
                )

        registry = Registry()

        for schema_id, resource in resources:
            registry = registry.with_resource(schema_id, resource)

        self.registry = registry

    def validate(self, contract_name, payload):
        """Raise jsonschema.ValidationError for invalid payloads."""
        if contract_name not in self.schemas:
            raise ValueError(
                f"Unsupported platform contract: {contract_name}"
            )

        validator = Draft202012Validator(
            self.schemas[contract_name],
            registry=self.registry,
            format_checker=FormatChecker(),
        )

        validator.validate(payload)
        return True

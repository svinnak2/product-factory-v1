# Product Factory platform interface (v0.1.0 candidate)

This is a **platform-facing registration candidate** for the independently executable Product Factory v6.1.6. It is intentionally separate from the internal `product-factory/factory.yaml` and `product-factory/registry.yaml`.

## Public capability

- `capability.product-definition`: accepts `contract.platform.execution-request` version `0.1.0` and declares `contract.platform.execution-result` version `0.1.0`.
- Supported platform work types: `new-product`, `new-capability`, `new-feature`, `development-defect`, `operations-defect`.
- Internal work-context terminology (`PRODUCT_CREATION`, `PRODUCT_EVOLUTION`) is retained; mapping must be implemented and tested before operational registration.

## Integration status

**Registration candidate only.** The execution adapter, platform work identity, human-interaction mapping, artifact publication, and runtime end-to-end integration are not yet implemented. Declared input/output contracts are an intended interface, **not evidence that the runtime currently accepts or emits them**.

The platform team must eventually place these three files under `factories/product-factory/` and add `factories/product-factory/catalog.yaml` to its root `contracts/catalog.yaml`. Neither action has been taken here.

## Internal implementation

The original Product Factory's CLI, runtime, agent definitions, output catalog, approvals, and 24-artifact workflow remain unchanged. Do not copy the original repository's shared `contracts/`, `policies/`, or `platform/` into the platform repository without contract-by-contract review.

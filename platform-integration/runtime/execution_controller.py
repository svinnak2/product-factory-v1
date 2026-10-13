"""Automatic execution and human-review continuation for Product Factory."""


class ProductExecutionController:
    """Drive Product Factory execution without bypassing governance gates."""

    def __init__(self, adapter, max_steps=30):
        if not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")

        self.adapter = adapter
        self.max_steps = max_steps

    def run_until_pause(self, identity):
        """Execute eligible artifacts until a pause or completion."""

        history = []

        for _ in range(self.max_steps):
            result = self.adapter.execute_next(identity)
            history.append(result)

            state = result["workflow_state"]

            if state not in ("READY_TO_RUN", "RUNNING"):
                return {
                    "workflow_state": state,
                    "execution_history": history,
                    "steps_executed": len(history),
                    "pending_actions": result.get("pending_actions", []),
                }

            if not result.get("artifact_generated"):
                return {
                    "workflow_state": state,
                    "execution_history": history,
                    "steps_executed": len(history),
                    "pending_actions": result.get("pending_actions", []),
                    "requires_attention": True,
                }

        raise RuntimeError(
            "Automatic execution reached its step limit; "
            "inspect session state before continuing"
        )

    def review_and_resume(self, identity, decision, comments, actor):
        """Record a human decision and resume only when eligible."""

        review = self.adapter.submit_review(
            identity,
            decision,
            comments,
            actor,
        )

        if review["workflow_state"] != "READY_TO_RUN":
            return {
                "review": review,
                "resumed": False,
                "execution": None,
            }

        execution = self.run_until_pause(identity)

        return {
            "review": review,
            "resumed": True,
            "execution": execution,
        }

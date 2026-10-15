"""Textual private fault API adapter and shape auditor.

Centralizes access to Textual's internal exception state:
- App._handle_exception
- App._exception
- App._exception_event
- App._return_code

Prevents scattered private attribute access, audits that the underlying Textual
App contract remains compatible, and surfaces shape drift loudly rather than
falsely claiming success (R02).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from textual.app import App

REQUIRED_APP_ATTRIBUTES: tuple[str, ...] = ("_return_code", "_exception", "_exception_event")
REQUIRED_CLASS_METHODS: tuple[str, ...] = ("_handle_exception",)


def audit_textual_app_contract(app: App[Any] | type[App[Any]] | Any) -> None:
    """Verify that a Textual App class or instance satisfies the required fault contract.

    Raises RuntimeError if Textual has altered or dropped its internal fault
    containment hooks or attributes, or if attributes/hooks are non-callable or unusable.
    """
    app_cls = app if isinstance(app, type) else type(app)

    # Class-level: verify required hooks exist and are callable
    for m in REQUIRED_CLASS_METHODS:
        attr = getattr(app_cls, m, None)
        if attr is None or not callable(attr):
            raise RuntimeError(
                f"Incompatible Textual App class {app_cls.__name__}: "
                f"missing or non-callable method {m!r}. "
                "Textual version may have altered its exception-handling hook structure."
            )

    # Instance-level contract audit
    if not isinstance(app, type):
        for m in REQUIRED_CLASS_METHODS:
            method = getattr(app, m, None)
            if method is None or not callable(method):
                raise RuntimeError(
                    f"Incompatible Textual App instance: missing or non-callable hook {m!r}."
                )

        for attr in REQUIRED_APP_ATTRIBUTES:
            if not hasattr(app, attr):
                raise RuntimeError(
                    f"Incompatible Textual App instance: missing attribute {attr!r}. "
                    "Textual version may have altered its exception-handling state structure."
                )

        # _exception_event must support set() notification (Textual uses asyncio.Event)
        event = getattr(app, "_exception_event", None)
        if event is None or not hasattr(event, "set") or not callable(event.set):
            raise RuntimeError(
                "Incompatible Textual App instance: "
                "_exception_event does not support callable set() notification."
            )


def record_unhandled_fault(app: App[Any] | Any, error: Exception, return_code: int = 3) -> None:
    """Record an unhandled exception onto the Textual App instance.

    Sets app._return_code and arms app._exception and app._exception_event if not yet set.
    Audits attribute presence so unsupported shapes fail explicitly rather than silently.
    Preserves Textual's first-fault semantics.
    """
    audit_textual_app_contract(app)
    app._return_code = return_code
    if app._exception is None:
        app._exception = error
        app._exception_event.set()


def get_unhandled_fault(app: App[Any] | Any) -> Exception | None:
    """Retrieve any unhandled exception recorded on the Textual App instance.

    Audits attribute presence so unexpected shape changes are not hidden.
    """
    audit_textual_app_contract(app)
    return getattr(app, "_exception", None)


__all__ = [
    "REQUIRED_APP_ATTRIBUTES",
    "REQUIRED_CLASS_METHODS",
    "audit_textual_app_contract",
    "get_unhandled_fault",
    "record_unhandled_fault",
]
